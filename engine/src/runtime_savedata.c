/* libSceSaveData on host directories:
 *   <user>/savedata/<user id>/<title id>/<dir name>/        files the game writes
 *   <user>/savedata/<user id>/<title id>/<dir name>.sce_sys/ param.bin, icon0.png
 *   <user>/savedata/<user id>/<title id>.memory/memory.dat  SaveDataMemory
 * A mounted directory appears to the guest as /savedata0../savedata15.
 * Metadata lives beside the directory so the guest's own files are untouched. */
#define _GNU_SOURCE
#include "runtime.h"
#include "gpu/bbgpu.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include <dirent.h>
#include <errno.h>
#include <sys/stat.h>
#include <unistd.h>
#ifndef _WIN32
#include <ftw.h>
#endif

#define ERR_PARAMETER ((int32_t)0x809F0000)
#define ERR_NOT_INITIALIZED ((int32_t)0x809F0001)
#define ERR_NOT_MOUNTED ((int32_t)0x809F0004)
#define ERR_EXISTS ((int32_t)0x809F0007)
#define ERR_NOT_FOUND ((int32_t)0x809F0008)
#define ERR_INTERNAL ((int32_t)0x809F000B)
#define ERR_MOUNT_FULL ((int32_t)0x809F000C)
#define ERR_BAD_MOUNTED ((int32_t)0x809F000D)
#define ERR_INVALID_USER ((int32_t)0x809F0011)
#define ERR_MEMORY_NOT_READY ((int32_t)0x809F0012)
#define MODE_RDONLY 1
#define MODE_CREATE 4
#define MODE_COPY_ICON 16
#define MODE_CREATE2 32
#define SLOTS 16

typedef struct { char data[10]; char pad[6]; } TitleId;
typedef struct { char data[32]; } DirName;
typedef struct { char data[16]; } MountPoint;
typedef struct {
    char title[128], subtitle[128], detail[1024];
    uint32_t user_param; int32_t pad;
    int64_t mtime;
    uint8_t reserved[32];
} Param;
typedef struct { int32_t user; int32_t pad; const TitleId *title; const DirName *dir; const void *fingerprint;
                 uint64_t blocks; uint32_t mode; uint8_t reserved[32]; } Mount1;
typedef struct { int32_t user; int32_t pad; const DirName *dir; uint64_t blocks; uint32_t mode;
                 uint8_t reserved[32]; int32_t pad2; } Mount2;
typedef struct { MountPoint point; uint64_t required_blocks; uint32_t unused, status; uint8_t reserved[28]; int32_t pad; } MountResult;
typedef struct { int32_t user; int32_t pad; const TitleId *title; const DirName *dir; uint32_t unused;
                 uint8_t reserved[32]; int32_t pad2; } Delete;
typedef struct { int32_t user; int32_t pad; const TitleId *title; const DirName *dir; uint32_t key, order;
                 uint8_t reserved[32]; } SearchCond;
typedef struct { uint64_t blocks, free_blocks; uint8_t reserved[32]; } SearchInfo;
typedef struct { uint32_t hits; int32_t pad; DirName *names; uint32_t names_capacity, set_count;
                 Param *params; SearchInfo *infos; uint8_t reserved[12]; int32_t pad2; } SearchResult;
typedef struct { const void *buffer; uint64_t buffer_size, data_size; uint8_t reserved[32]; } Icon;
_Static_assert(sizeof(Param)==1328,"OrbisSaveDataParam layout");
_Static_assert(sizeof(Mount1)==80 && sizeof(Mount2)==64,"OrbisSaveDataMount layouts");
_Static_assert(sizeof(MountResult)==64,"OrbisSaveDataMountResult layout");
_Static_assert(sizeof(SearchCond)==64 && sizeof(SearchResult)==56,"dir name search layouts");

static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static int initialized;
static char title_id[16]="UNKNOWN";
static struct { int used, writable; char host[700], meta[700]; } slots[SLOTS];
static char memory_path[720];
static uint64_t memory_size;
static size_t mounts_done, memory_writes;

/* Bloodborne "sound hack" (rainvmaker, from the Diegolix29 shadPS4 fork): the game data
 * save carries a flag at 0x204E of userdata0010; with it clear, parts of the game's audio
 * (e.g. the player's weapon sounds) never play. It is set before the game reads the save.
 * BB_SOUND_HACK=0 leaves saves untouched. */
static void bloodborne_sound_hack(void) {
    static const char *const ids[]={"CUSA00207","CUSA00208","CUSA00299","CUSA00900","CUSA01363","CUSA03014","CUSA03023","CUSA03173"};
    const char *env=getenv("BB_SOUND_HACK");
    if (env && env[0]=='0') return;
    int bloodborne=0;
    for (size_t i=0;i<sizeof(ids)/sizeof(*ids);++i) if (!strcmp(title_id,ids[i])) bloodborne=1;
    if (!bloodborne) return;
    char users[700];
    snprintf(users,sizeof(users),"%s/savedata",runtime_file_user_dir());
    DIR *dir=opendir(users);
    if (!dir) return;
    for (struct dirent *e; (e=readdir(dir));) {
        if (e->d_name[0]=='.') continue;
        char path[1100];
        snprintf(path,sizeof(path),"%s/%s/%s/SPRJ0005/userdata0010",users,e->d_name,title_id);
        FILE *f=fopen(path,"r+b");
        if (!f) continue;
        int old=fseek(f,0x204E,SEEK_SET) ? EOF : fgetc(f);
        if (old!=EOF && old!=1 && !fseek(f,0x204E,SEEK_SET)) {
            fputc(1,f);
            printf("Runtime: Bloodborne sound flag set in %s (was %d)\n",path,old);
        }
        fclose(f);
    }
    closedir(dir);
}
void runtime_savedata_configure(const char *title) {
    if (title && *title) snprintf(title_id,sizeof(title_id),"%s",title);
    bloodborne_sound_hack();
}

static int make_dirs(const char *path) {
    char buffer[700];
    snprintf(buffer,sizeof(buffer),"%s",path);
    for (char *p=buffer+1;*p;++p) if (*p=='/') { *p=0; mkdir(buffer,0755); *p='/'; }
    return mkdir(buffer,0755) && errno!=EEXIST ? -1 : 0;
}
static void root(int32_t user, const char *title, char *out, size_t size) {
    snprintf(out,size,"%s/savedata/%d/%s",runtime_file_user_dir(),user,title && *title ? title : title_id);
}
static int valid_name(const char *name, size_t max) {
    size_t n=strnlen(name,max);
    if (!n || n==max) return 0;
    for (size_t i=0;i<n;++i) if (name[i]=='/' || name[i]=='\\' || (name[i]=='.' && (i==0 || name[i-1]=='.'))) return 0;
    return 1;
}
/* A whole file replaced in one rename (a crash mid-write keeps the old one). */
static int write_atomic(const char *path, const void *data, size_t size) {
    char temp[760]; snprintf(temp,sizeof(temp),"%s.bbtmp",path);
    FILE *f=fopen(temp,"wb");
    if (!f) return -1;
    int ok=fwrite(data,1,size,f)==size && !fflush(f) && !fsync(fileno(f));
    ok=!fclose(f) && ok;
    if (!ok || runtime_file_replace(temp,path)) { unlink(temp); return -1; }
    return 0;
}
static void write_param(const char *meta, const Param *p) {
    char path[700]; snprintf(path,sizeof(path),"%s/param.bin",meta);
    Param copy=*p; copy.mtime=time(NULL);
    write_atomic(path,&copy,sizeof(copy));
}
static int read_param(const char *meta, Param *p) {
    char path[700]; snprintf(path,sizeof(path),"%s/param.bin",meta);
    memset(p,0,sizeof(*p));
    FILE *f=fopen(path,"rb");
    if (!f) return -1;
    size_t n=fread(p,sizeof(*p),1,f); fclose(f);
    struct stat st;
    if (!stat(path,&st)) p->mtime=st.st_mtime;
    return n==1 ? 0 : -1;
}
/* The save list (runtime_services.c; runtime.h): a save of the dialog's user and title. */
int runtime_savedata_param(int32_t user, const char *title, const char *dir, void *param) {
    if (!valid_name(dir,32)) return -1;
    char base[600], meta[680];
    root(user,title,base,sizeof(base));
    snprintf(meta,sizeof(meta),"%s/%s.sce_sys",base,dir);
    return read_param(meta,(Param *)param);
}
int runtime_savedata_exists(int32_t user, const char *title, const char *dir) {
    if (!valid_name(dir,32)) return 0;
    char base[600], host[640];
    root(user,title,base,sizeof(base));
    snprintf(host,sizeof(host),"%s/%s",base,dir);
    struct stat st;
    return !stat(host,&st) && S_ISDIR(st.st_mode);
}
/* Host path of a save's picture in the save list: thumb.png (the game in play when it was written) when there is
 * one, else the game's icon0.png; 0 when named. */
int runtime_savedata_icon(int32_t user, const char *title, const char *dir, char *out, size_t size) {
    if (!valid_name(dir,32)) return -1;
    char base[600];
    root(user,title,base,sizeof(base));
    struct stat st;
    snprintf(out,size,"%s/%s.sce_sys/thumb.png",base,dir);
    if (!stat(out,&st) && st.st_size>0) return 0;
    snprintf(out,size,"%s/%s.sce_sys/icon0.png",base,dir);
    return 0;
}
/* Deleting a save from the save list (Delete / Triangle twice): its folders move to
 * <user>/savedata-deleted/<user id>/<title>/<dir>-<YYYYmmdd-HHMMSS>/ beside savedata, where the launcher lists
 * them and moves them back: <dir>, <dir>.sce_sys and, when there is one, .backup/<dir> as "backup". 0 when moved;
 * a mounted save is refused. */
int runtime_savedata_trash(int32_t user, const char *title, const char *dir) {
    if (!valid_name(dir,32)) return -1;
    char base[600], host[640], meta[680], backup[700], trash[700];
    root(user,title,base,sizeof(base));
    snprintf(host,sizeof(host),"%s/%s",base,dir);
    snprintf(meta,sizeof(meta),"%s/%s.sce_sys",base,dir);
    snprintf(backup,sizeof(backup),"%s/.backup/%s",base,dir);
    pthread_mutex_lock(&lock);
    for (int i=0;i<SLOTS;++i)
        if (slots[i].used && !strcmp(slots[i].host,host)) { pthread_mutex_unlock(&lock); return -1; }
    char stamp[32]; time_t now=time(NULL); struct tm tm;
    if (!localtime_r(&now,&tm)) memset(&tm,0,sizeof(tm));
    strftime(stamp,sizeof(stamp),"%Y%m%d-%H%M%S",&tm);
    snprintf(trash,sizeof(trash),"%s/savedata-deleted/%d/%s/%s-%s",runtime_file_user_dir(),user,
             title && *title ? title : title_id,dir,stamp);
    /* The folder, its picture and text and its last good copy move together: a rename that fails (a file held
     * open elsewhere) puts back the ones already done, so the save is never split between its place and the
     * trash (a backup left behind would later "repair" a new save of that name with old files). */
    struct stat st;
    char to_host[760], to_meta[760], to_backup[760];
    snprintf(to_host,sizeof(to_host),"%s/%s",trash,dir);
    snprintf(to_meta,sizeof(to_meta),"%s/%s.sce_sys",trash,dir);
    snprintf(to_backup,sizeof(to_backup),"%s/backup",trash);
    const int has_meta=!stat(meta,&st), has_backup=!stat(backup,&st);
    int r=stat(host,&st) || make_dirs(trash) ? -1 : 0;
    int moved=0; /* 1 host, 2 + meta, 3 + backup */
    if (!r) r=rename(host,to_host) ? -1 : (moved=1, 0);
    if (!r && has_meta) r=rename(meta,to_meta) ? -1 : (moved=2, 0);
    if (!r && has_backup) r=rename(backup,to_backup) ? -1 : (moved=3, 0);
    if (r) {
        if (moved>=2 && has_meta) rename(to_meta,meta);
        if (moved>=1) rename(to_host,host);
        rmdir(trash);
    }
    pthread_mutex_unlock(&lock);
    printf("Runtime: save data '%s' %s %s\n",dir,r ? "could not be moved to" : "moved to",trash);
    return r;
}
#ifdef _WIN32
static void remove_tree(const char *path) { compat_remove_tree(path); }
#else
static int remove_entry(const char *path, const struct stat *st, int flag, struct FTW *ftw) {
    (void)st; (void)flag; (void)ftw; return remove(path);
}
static void remove_tree(const char *path) { nftw(path,remove_entry,16,FTW_DEPTH|FTW_PHYS); }
#endif

static ABI int32_t save_initialize(const void *param) { (void)param; initialized=1; return 0; }
static ABI int32_t save_terminate(void) {
    if (!initialized) return ERR_NOT_INITIALIZED;
    initialized=0; return 0;
}
/* The overlay's save slots (gpu/shim/bbport_saves.cpp): the folder of this title's saves, whether the game has
 * any save open right now, and a slot chosen in the overlay ("Load", which restarts the game) put back before
 * the game opens its first save. */
static int32_t last_user=1;
void bbport_saves_apply_pending(void);
void bbport_saves_closed(const char *host_dir);
int runtime_savedata_dir(char *out, size_t size) { root(last_user,NULL,out,size); return 0; }
int runtime_savedata_mounted(void) {
    pthread_mutex_lock(&lock);
    int n=0;
    for (int i=0;i<SLOTS;++i) n+=slots[i].used;
    pthread_mutex_unlock(&lock);
    return n;
}
/* Practice mode (checkpoint jumps, runtime_checkpoint.c): the campaign save of the running game (SAVEDATA0<game>0)
 * is the practice copy the overlay made before the first jump, for mounting and for deleting alike (a game deleting
 * its campaign save, on New Game say, must not delete the player's own). */
static void practice_redirect(const char *base, const char *name, char *host, size_t host_size, char *meta,
                              size_t meta_size) {
    if (!runtime_checkpoint_practice()) return;
    const char *exe=getenv("BB_EXE");
    const int game=!exe ? 0 : strstr(exe,"big3") ? 3 : strstr(exe,"big2") ? 2 : !strcmp(exe,"eboot.bin") ? 1 : 0;
    char campaign[16];
    snprintf(campaign,sizeof(campaign),"SAVEDATA0%d0",game);
    if (game && !strcmp(name,campaign)) {
        snprintf(host,host_size,"%s.backups/u%d/practice/%s",base,game,name);
        snprintf(meta,meta_size,"%s.backups/u%d/practice/%s.sce_sys",base,game,name);
    }
}
static int32_t mount(int32_t user, const char *title, const DirName *dir, uint32_t mode, MountResult *result) {
    if (!initialized) return ERR_NOT_INITIALIZED;
    if (user<0) return ERR_INVALID_USER;
    static pthread_once_t pending_once=PTHREAD_ONCE_INIT;
    last_user=user;
    pthread_once(&pending_once,bbport_saves_apply_pending);
    if (!dir || !result || !valid_name(dir->data,sizeof(dir->data))) return ERR_PARAMETER;
    char base[600], host[640], meta[680];
    root(user,title,base,sizeof(base));
    snprintf(host,sizeof(host),"%s/%s",base,dir->data);
    snprintf(meta,sizeof(meta),"%s/%s.sce_sys",base,dir->data);
    practice_redirect(base,dir->data,host,sizeof(host),meta,sizeof(meta));
    struct stat st;
    int exists=!stat(host,&st) && S_ISDIR(st.st_mode);
    if ((mode & MODE_CREATE) && exists) return ERR_EXISTS;
    if (!(mode & (MODE_CREATE|MODE_CREATE2)) && !exists) return ERR_NOT_FOUND;
    pthread_mutex_lock(&lock);
    int slot=-1;
    for (int i=0;i<SLOTS;++i) {
        if (slots[i].used && !strcmp(slots[i].host,host)) { pthread_mutex_unlock(&lock); return ERR_BAD_MOUNTED; }
        if (!slots[i].used && slot<0) slot=i;
    }
    if (slot<0) { pthread_mutex_unlock(&lock); return ERR_MOUNT_FULL; }
    if (!exists && (make_dirs(host) || make_dirs(meta))) { pthread_mutex_unlock(&lock); return ERR_INTERNAL; }
    if (!exists) { Param empty={0}; write_param(meta,&empty); }
    slots[slot].used=1;
    slots[slot].writable=!(mode & MODE_RDONLY);
    snprintf(slots[slot].host,sizeof(slots[slot].host),"%s",host);
    snprintf(slots[slot].meta,sizeof(slots[slot].meta),"%s",meta);
    memset(result,0,sizeof(*result));
    char point[32];
    snprintf(point,sizeof(point),"/savedata%d",slot&15);
    memcpy(result->point.data,point,strlen(point)+1);
    result->status=exists ? 0 : 1; /* CREATED */
    if (runtime_file_mount(result->point.data,host)) {
        /* No mount behind it: say so rather than report a mount every file call would fail on. */
        slots[slot].used=0;
        pthread_mutex_unlock(&lock);
        return ERR_MOUNT_FULL;
    }
    ++mounts_done;
    pthread_mutex_unlock(&lock);
    printf("Runtime: save data '%s' mounted at %s (%s%s)\n",dir->data,result->point.data,
           exists ? "existing" : "created",(mode & MODE_RDONLY) ? ", read-only" : "");
    return 0;
}
static ABI int32_t save_mount(const Mount1 *m, MountResult *result) {
    if (!m) return ERR_PARAMETER;
    return mount(m->user,m->title ? m->title->data : NULL,m->dir,m->mode,result);
}
static ABI int32_t save_mount2(const Mount2 *m, MountResult *result) {
    if (!m) return ERR_PARAMETER;
    return mount(m->user,NULL,m->dir,m->mode,result);
}
static int slot_of(const MountPoint *point) {
    if (!point || strncmp(point->data,"/savedata",9)) return -1;
    int slot=atoi(point->data+9);
    return slot>=0 && slot<SLOTS && slots[slot].used ? slot : -1;
}
static ABI int32_t save_umount(const MountPoint *point) {
    if (!initialized) return ERR_NOT_INITIALIZED;
    pthread_mutex_lock(&lock);
    int slot=slot_of(point);
    char host[700]="", picture[720]="", loaded[720]=""; /* a written save gets the last picture of the game in play (bbport_thumbnail) */
    if (slot>=0) {
        runtime_file_unmount(point->data);
        slots[slot].used=0;
        snprintf(host,sizeof(host),"%s",slots[slot].host);
        if (slots[slot].writable) snprintf(picture,sizeof(picture),"%s/thumb.png",slots[slot].meta);
        else { /* a game save read (loaded) that has no picture yet: it gets one from where it starts */
            const char *name=strrchr(slots[slot].meta,'/');
            name=name ? name+1 : slots[slot].meta;
            if (!strncmp(name,"SAVEDATA0",9) && name[9]>='1' && name[9]<='3' && name[10]>='0' && name[10]<='9' &&
                !strcmp(name+11,".sce_sys")) {
                char thumb[720]; snprintf(thumb,sizeof(thumb),"%s/thumb.png",slots[slot].meta);
                FILE *f=fopen(thumb,"rb");
                if (f) fclose(f);
                else snprintf(loaded,sizeof(loaded),"%s",thumb);
            }
        }
    }
    pthread_mutex_unlock(&lock);
    if (slot<0) return ERR_NOT_FOUND;
    /* A save closed: the overlay's story save follows the game's campaign saves (bbport_saves.cpp). */
    bbport_saves_closed(host);
    const int written=picture[0] ? bbgpu_thumbnail_save(picture) : 0;
    /* written==2: the picture follows once play goes on (or at exit); the older one stays meanwhile */
    if (written) printf("Runtime: save picture %s (%s)\n",written==1 ? "written" : "waits for play to go on",picture);
    if (loaded[0]) {
        bbgpu_thumbnail_loaded(loaded);
        printf("Runtime: save picture waits for play (%s, loaded)\n",loaded);
    }
    return 0;
}
static ABI int32_t save_set_param(const MountPoint *point, uint32_t type, const void *buffer, uint64_t size) {
    if (!initialized) return ERR_NOT_INITIALIZED;
    if (!buffer) return ERR_PARAMETER;
    pthread_mutex_lock(&lock);
    int slot=slot_of(point);
    if (slot<0) { pthread_mutex_unlock(&lock); return ERR_NOT_MOUNTED; }
    Param p; read_param(slots[slot].meta,&p);
    switch (type) {
    case 0: if (size<sizeof(Param)) goto bad; memcpy(&p,buffer,sizeof(p)); break;     /* ALL */
    case 1: snprintf(p.title,sizeof(p.title),"%.*s",(int)size,(const char *)buffer); break;
    case 2: snprintf(p.subtitle,sizeof(p.subtitle),"%.*s",(int)size,(const char *)buffer); break;
    case 3: snprintf(p.detail,sizeof(p.detail),"%.*s",(int)size,(const char *)buffer); break;
    case 4: if (size<4) goto bad; memcpy(&p.user_param,buffer,4); break;
    default: goto bad;
    }
    write_param(slots[slot].meta,&p);
    pthread_mutex_unlock(&lock);
    return 0;
bad:
    pthread_mutex_unlock(&lock);
    return ERR_PARAMETER;
}
static ABI int32_t save_icon(const MountPoint *point, const Icon *icon) {
    if (!initialized) return ERR_NOT_INITIALIZED;
    if (!icon || !icon->buffer) return ERR_PARAMETER;
    pthread_mutex_lock(&lock);
    int slot=slot_of(point);
    int32_t r=ERR_NOT_MOUNTED;
    if (slot>=0) {
        char path[700]; snprintf(path,sizeof(path),"%s/icon0.png",slots[slot].meta);
        r=write_atomic(path,icon->buffer,icon->data_size) ? ERR_INTERNAL : 0;
    }
    pthread_mutex_unlock(&lock);
    return r;
}
static ABI int32_t save_delete(const Delete *d) {
    if (!initialized) return ERR_NOT_INITIALIZED;
    if (!d || !d->dir || !valid_name(d->dir->data,sizeof(d->dir->data))) return ERR_PARAMETER;
    char base[600], host[640], meta[680];
    root(d->user,d->title ? d->title->data : NULL,base,sizeof(base));
    snprintf(host,sizeof(host),"%s/%s",base,d->dir->data);
    snprintf(meta,sizeof(meta),"%s/%s.sce_sys",base,d->dir->data);
    practice_redirect(base,d->dir->data,host,sizeof(host),meta,sizeof(meta));
    struct stat st;
    if (stat(host,&st)) return ERR_NOT_FOUND;
    remove_tree(host);
    remove_tree(meta);
    printf("Runtime: save data '%s' deleted\n",d->dir->data);
    return 0;
}
/* An existing slot of a save list (slots that do not exist are not listed, as on the console):
 * which = 0 first, 1 last, 2 latest written, 3 oldest, 4 the one named focus.
 * Returns 1 with the slot in out (and its parameters), or -1 when there is none. */
int runtime_savedata_pick(int32_t user, const char *title, const char (*names)[32], uint32_t count,
                          int which, const char *focus, char out[32], void *param_out) {
    char base[600];
    root(user,title,base,sizeof(base));
    int best=-1;
    Param p, best_param;
    memset(&best_param,0,sizeof(best_param));
    for (uint32_t i=0;names && i<count;++i) {
        char name[33]; memcpy(name,names[i],32); name[32]=0;
        if (!valid_name(name,sizeof(name))) continue;
        char host[640], meta[680];
        snprintf(host,sizeof(host),"%s/%s",base,name);
        snprintf(meta,sizeof(meta),"%s/%s.sce_sys",base,name);
        struct stat st;
        if (stat(host,&st) || !S_ISDIR(st.st_mode)) continue;
        read_param(meta,&p);
        int better = which==0 ? best<0 : which==1 ? 1 : which==2 ? best<0 || p.mtime>best_param.mtime
                   : which==3 ? best<0 || p.mtime<best_param.mtime : focus && !strncmp(focus,name,32);
        if (better) { best=(int)i; best_param=p; }
    }
    if (best<0) return -1;
    memcpy(out,names[best],32);
    if (param_out) memcpy(param_out,&best_param,sizeof(best_param));
    return 1;
}
/* SQL-LIKE pattern: % any run, _ one character. */
static int like(const char *s, const char *p) {
    if (!*p) return !*s;
    if (*p=='%') { for (;;++s) { if (like(s,p+1)) return 1; if (!*s) return 0; } }
    return *s && (*p=='_' || *p==*s) && like(s+1,p+1);
}
typedef struct { char name[32]; Param param; } Entry;
static uint32_t sort_key, sort_order;
static int compare(const void *a, const void *b) {
    const Entry *x=a, *y=b;
    int c = sort_key==1 ? (x->param.user_param>y->param.user_param)-(x->param.user_param<y->param.user_param)
          : sort_key==3 ? (x->param.mtime>y->param.mtime)-(x->param.mtime<y->param.mtime)
          : strcmp(x->name,y->name);
    return sort_order ? -c : c;
}
static ABI int32_t save_search(const SearchCond *cond, SearchResult *result) {
    if (!initialized) return ERR_NOT_INITIALIZED;
    if (!cond || !result) return ERR_PARAMETER;
    char base[600];
    root(cond->user,cond->title ? cond->title->data : NULL,base,sizeof(base));
    Entry *entries=NULL; size_t count=0, capacity=0;
    DIR *d=opendir(base);
    for (struct dirent *e; d && (e=readdir(d));) {
        size_t n=strlen(e->d_name);
        if (e->d_name[0]=='.' || n>=32 || (n>8 && !strcmp(e->d_name+n-8,".sce_sys"))) continue;
        if (cond->dir && cond->dir->data[0] && !like(e->d_name,cond->dir->data)) continue;
        if (count==capacity) { capacity=capacity ? capacity*2 : 16; entries=realloc(entries,capacity*sizeof(*entries)); }
        snprintf(entries[count].name,32,"%s",e->d_name);
        char meta[680]; snprintf(meta,sizeof(meta),"%s/%s.sce_sys",base,e->d_name);
        read_param(meta,&entries[count].param);
        ++count;
    }
    if (d) closedir(d);
    sort_key=cond->key; sort_order=cond->order;
    if (count) qsort(entries,count,sizeof(*entries),compare);
    result->hits=(uint32_t)count;
    uint32_t set=count<result->names_capacity ? (uint32_t)count : result->names_capacity;
    for (uint32_t i=0;i<set;++i) {
        if (result->names) memcpy(result->names[i].data,entries[i].name,32);
        if (result->params) result->params[i]=entries[i].param;
        if (result->infos) { memset(&result->infos[i],0,sizeof(SearchInfo)); result->infos[i].blocks=32768; result->infos[i].free_blocks=16384; }
    }
    result->set_count=set;
    free(entries);
    return 0;
}
/* SaveDataMemory: one fixed-size blob per user/title. */
static ABI int32_t memory_setup(int32_t user, uint64_t size, const Param *param) {
    if (!initialized) return ERR_NOT_INITIALIZED;
    if (!size) return ERR_PARAMETER;
    char base[600], dir[640];
    root(user,NULL,base,sizeof(base));
    snprintf(dir,sizeof(dir),"%s.memory",base);
    if (make_dirs(dir)) return ERR_INTERNAL;
    pthread_mutex_lock(&lock);
    snprintf(memory_path,sizeof(memory_path),"%s/memory.dat",dir);
    FILE *f=fopen(memory_path,"r+b");
    if (!f) f=fopen(memory_path,"w+b");
    int32_t r=ERR_INTERNAL;
    if (f) {
        fseek(f,0,SEEK_END);
        if ((uint64_t)ftell(f)<size && ftruncate(fileno(f),(off_t)size)) goto done;
        memory_size=size; r=0;
    done:
        fclose(f);
    }
    if (!r && param) write_param(dir,param);
    pthread_mutex_unlock(&lock);
    if (!r) printf("Runtime: save data memory ready (%llu bytes)\n",(unsigned long long)size);
    return r;
}
static int32_t memory_io(void *buffer, uint64_t size, int64_t offset, int write) {
    if (!initialized) return ERR_NOT_INITIALIZED;
    if (!buffer || offset<0) return ERR_PARAMETER;
    pthread_mutex_lock(&lock);
    if (!memory_size) { pthread_mutex_unlock(&lock); return ERR_MEMORY_NOT_READY; }
    if ((uint64_t)offset+size>memory_size) { pthread_mutex_unlock(&lock); return ERR_PARAMETER; }
    FILE *f=fopen(memory_path,"r+b");
    int32_t r=ERR_INTERNAL;
    if (f && !fseek(f,offset,SEEK_SET) &&
        (write ? fwrite(buffer,1,size,f) : fread(buffer,1,size,f))==size) r=0;
    if (f) fclose(f);
    if (!r && write) ++memory_writes;
    pthread_mutex_unlock(&lock);
    return r;
}
static ABI int32_t memory_get(int32_t user, void *buffer, uint64_t size, int64_t offset) { (void)user; return memory_io(buffer,size,offset,0); }
static ABI int32_t memory_set(int32_t user, void *buffer, uint64_t size, int64_t offset) { (void)user; return memory_io(buffer,size,offset,1); }

static const RuntimeExport exports[]={
    {"sceSaveDataInitialize",save_initialize}, {"sceSaveDataInitialize2",save_initialize},
    {"sceSaveDataInitialize3",save_initialize}, {"sceSaveDataTerminate",save_terminate},
    {"sceSaveDataMount",save_mount}, {"sceSaveDataMount2",save_mount2}, {"sceSaveDataUmount",save_umount},
    {"sceSaveDataSetParam",save_set_param}, {"sceSaveDataSaveIcon",save_icon}, {"sceSaveDataDelete",save_delete},
    {"sceSaveDataDirNameSearch",save_search},
    {"sceSaveDataSetupSaveDataMemory",memory_setup}, {"sceSaveDataGetSaveDataMemory",memory_get},
    {"sceSaveDataSetSaveDataMemory",memory_set},
};
uintptr_t runtime_savedata_resolve(const char *name) { return RUNTIME_LOOKUP(exports,name); }
void runtime_savedata_report(void) { printf("Runtime: save data mounts=%zu, memory writes=%zu\n",mounts_done,memory_writes); }

