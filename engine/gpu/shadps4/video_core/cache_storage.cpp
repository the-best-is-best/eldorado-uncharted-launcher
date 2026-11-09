// SPDX-FileCopyrightText: Copyright 2025-2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include "common/elf_info.h"
#include "common/io_file.h"
#include "common/polyfill_thread.h"
#include "common/thread.h"
#include "core/emulator_settings.h"
#include "bbport_nan_guard.h"

#include "video_core/cache_storage.h"
#include "video_core/renderer_vulkan/vk_instance.h"
#include "video_core/renderer_vulkan/vk_pipeline_cache.h"

#include <miniz.h>
#include <cstring>
#include <filesystem>
#include <unordered_map>
#include <xxhash.h>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <thread>

#include <array>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <functional>
#include <future>
#include <mutex>
#include <queue>

namespace {

// bbport: several writer threads (a first shader preparation writes ~25,000 files, 27 s on one thread). A file always
// goes to the same thread (by its path), so the writes and removals of one file keep their order.
struct IoQueue {
    std::mutex mutex;
    std::condition_variable_any cv;
    std::queue<std::packaged_task<void()>> requests;
};
std::array<IoQueue, Storage::DataBase::IoWorkers> io_queues{};
std::atomic<u32> num_requests{};

mz_zip_archive zip_ar{};
bool ar_is_read_only{true};

// El Dorado: the folder cache as one pack file per game (blobs.pack) instead of one small file per blob. 33,234 files
// (663 MB) were written at ~500 a second, the four writers stalling together for 1.3-2.9 s at a time (create and
// rename in one folder), so a new cache was still being written a minute into play. Records are appended by one
// writer: "BBPK", flags (1: removed), name length, data size, XXH3 of the data, the name, the data. An index in
// memory says where each blob is; a torn record at the end (a game closed mid-write) is cut off at the next open,
// and a pack more than a third dead is rewritten. BB_SHADER_CACHE_FILES=1: one file per blob as before.
constexpr u32 PackMagic = 0x4b504242; // "BBPK"
struct PackHeader {
    u32 magic;
    u16 flags;
    u16 name_size;
    u32 data_size;
    u64 hash;
};
static_assert(sizeof(PackHeader) == 24);
struct PackEntry {
    u64 offset; ///< of the data
    u32 size;
    u64 hash;
};
bool pack_mode = false;
std::filesystem::path pack_path;
std::mutex pack_mutex; ///< pack_index, pack_end, pack_dead
std::unordered_map<std::string, PackEntry> pack_index; ///< "name.ext"
u64 pack_end = 0, pack_dead = 0;
std::FILE* pack_writer = nullptr; ///< used by the one writer thread only (and Open/Clear/Close around it)
std::atomic<u32> pack_generation{0}; ///< bumped when the file is replaced: readers reopen

bool UsePack() {
    static const bool files = [] {
        const char* env = std::getenv("BB_SHADER_CACHE_FILES");
        return env && env[0] == '1';
    }();
    return !files;
}

int PackSeek(std::FILE* f, u64 at) {
#ifdef _WIN32
    return _fseeki64(f, static_cast<long long>(at), SEEK_SET);
#else
    return fseeko(f, static_cast<off_t>(at), SEEK_SET);
#endif
}

/// This thread's read handle of the pack (close: it is closed, so the file can be replaced).
std::FILE* PackReader(bool close = false) {
    thread_local std::FILE* reader = nullptr;
    thread_local u32 generation = ~0u;
    if (close) {
        if (reader) {
            std::fclose(reader);
        }
        reader = nullptr;
        return nullptr;
    }
    const u32 now = pack_generation.load(std::memory_order_acquire);
    if (!reader || generation != now) {
        if (reader) {
            std::fclose(reader);
        }
        reader = std::fopen(pack_path.string().c_str(), "rb");
        generation = now;
    }
    return reader;
}

/// Appends one record (writer thread); returns the data's offset, or ~0 when the write failed.
u64 PackAppend(const std::string& key, u16 flags, const void* data, u32 size, u64 hash) {
    if (!pack_writer) {
        return ~0ull;
    }
    const PackHeader header{PackMagic, flags, u16(key.size()), size, hash};
    u64 start;
    {
        std::scoped_lock lk{pack_mutex};
        start = pack_end;
    }
    const bool ok = std::fwrite(&header, sizeof(header), 1, pack_writer) == 1 &&
                    std::fwrite(key.data(), 1, key.size(), pack_writer) == key.size() &&
                    (!size || std::fwrite(data, 1, size, pack_writer) == size) && std::fflush(pack_writer) == 0;
    std::scoped_lock lk{pack_mutex};
    if (!ok) {
        return ~0ull;
    }
    pack_end = start + sizeof(header) + key.size() + size;
    return start + sizeof(header) + key.size();
}

/// Reads the pack's records into the index; cuts a torn end. Returns the live bytes.
void PackScan() {
    pack_index.clear();
    pack_end = pack_dead = 0;
    std::FILE* f = std::fopen(pack_path.string().c_str(), "rb");
    if (!f) {
        return;
    }
    std::error_code ec;
    const u64 file_size = std::filesystem::file_size(pack_path, ec);
    u64 at = 0;
    std::string key;
    while (at + sizeof(PackHeader) <= file_size) {
        PackHeader header{};
        if (PackSeek(f, at) != 0 || std::fread(&header, sizeof(header), 1, f) != 1 ||
            header.magic != PackMagic || at + sizeof(header) + header.name_size + header.data_size > file_size) {
            break;
        }
        key.resize(header.name_size);
        if (header.name_size && std::fread(key.data(), 1, header.name_size, f) != header.name_size) {
            break;
        }
        const u64 data_at = at + sizeof(header) + header.name_size;
        if (const auto it = pack_index.find(key); it != pack_index.end()) {
            pack_dead += sizeof(PackHeader) + key.size() + it->second.size;
            pack_index.erase(it);
        }
        if (header.flags & 1) {
            pack_dead += sizeof(PackHeader) + key.size();
        } else {
            pack_index[key] = {data_at, header.data_size, header.hash};
        }
        at = data_at + header.data_size;
    }
    std::fclose(f);
    pack_end = at;
    if (at < file_size) {
        std::filesystem::resize_file(pack_path, at, ec);
        std::printf("Shader cache: a torn record at the end of the pack cut off (%llu bytes)\n",
                    static_cast<unsigned long long>(file_size - at));
    }
}

bool PackRead(const PackEntry& entry, void* out) {
    std::FILE* reader = PackReader();
    if (!reader || PackSeek(reader, entry.offset) != 0 ||
        std::fread(out, 1, entry.size, reader) != entry.size) {
        return false;
    }
    return XXH3_64bits(out, entry.size) == entry.hash;
}

/// Writes the live records into a new pack and puts it in place (Open, before any writer runs).
void PackCompact() {
    const auto temp = std::filesystem::path{pack_path}.concat(".new");
    std::FILE* out = std::fopen(temp.string().c_str(), "wb");
    if (!out) {
        return;
    }
    std::unordered_map<std::string, PackEntry> index;
    u64 at = 0;
    std::vector<u8> data;
    bool ok = true;
    for (const auto& [key, entry] : pack_index) {
        data.resize(entry.size);
        if (!PackRead(entry, data.data())) {
            continue;
        }
        const PackHeader header{PackMagic, 0, u16(key.size()), entry.size, entry.hash};
        ok = std::fwrite(&header, sizeof(header), 1, out) == 1 &&
             std::fwrite(key.data(), 1, key.size(), out) == key.size() &&
             (!entry.size || std::fwrite(data.data(), 1, entry.size, out) == entry.size);
        if (!ok) {
            break;
        }
        index[key] = {at + sizeof(header) + key.size(), entry.size, entry.hash};
        at += sizeof(header) + key.size() + entry.size;
    }
    ok = std::fclose(out) == 0 && ok;
    PackReader(true); // Windows replaces no file still open here
    std::error_code ec;
    if (ok) {
        pack_generation.fetch_add(1, std::memory_order_acq_rel);
        std::filesystem::rename(temp, pack_path, ec);
    }
    if (!ok || ec) {
        std::filesystem::remove(temp, ec);
        return;
    }
    std::printf("Shader cache: pack rewritten without its removed records (%llu -> %llu bytes)\n",
                static_cast<unsigned long long>(pack_end), static_cast<unsigned long long>(at));
    pack_index = std::move(index);
    pack_end = at;
    pack_dead = 0;
}

} // namespace

namespace Storage {

void ProcessIO(const std::stop_token& stoken, u32 index) {
    Common::SetCurrentThreadName("shadPS4:PipelineCacheIO");
    auto& io = io_queues[index];
    while (true) {
        std::packaged_task<void()> request{};
        {
            std::unique_lock lk{io.mutex};
            Common::CondvarWait(io.cv, lk, stoken, [&] { return !io.requests.empty(); });
            if (stoken.stop_requested()) {
                return;
            }
            if (io.requests.empty()) {
                continue;
            }
            request = std::move(io.requests.front());
            io.requests.pop();
        }
        if (request.valid()) {
            const auto start = std::chrono::steady_clock::now();
            request();
            request.get_future().wait();
            // A write over a second: Windows held the file call (seen at an exit after a preparation, all writers
            // stuck in create/rename; an antivirus scanning each new file is the likely cause).
            const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                                std::chrono::steady_clock::now() - start).count();
            if (ms > 1000) {
                std::printf("Shader cache: one write took %lld ms (writer %u, %u queued)\n",
                            static_cast<long long>(ms), index, num_requests.load());
            }
        }
        --num_requests;
    }
}

/// The writer of a file: always the same one for a path (one writer for an archive: miniz is not thread-safe).
static void Enqueue(const std::filesystem::path& path, std::packaged_task<void()>&& request) {
    const u32 index = EmulatorSettings.IsPipelineCacheArchived() || pack_mode
                          ? 0
                          : u32(std::filesystem::hash_value(path) % DataBase::IoWorkers);
    auto& io = io_queues[index];
    {
        std::scoped_lock lock{io.mutex};
        io.requests.emplace(std::move(request));
        ++num_requests;
    }
    io.cv.notify_one();
}

constexpr std::string GetBlobFileExtension(BlobType type);

/// The pack in this game's cache folder: loose blob files of the old layout go into it first (and are removed).
void OpenPack(const std::filesystem::path& folder) {
    pack_mode = true;
    pack_path = folder / "blobs.pack";
    {
        std::scoped_lock lk{pack_mutex};
        PackScan();
        if (pack_end > (16ull << 20) && pack_dead * 3 > pack_end) {
            PackCompact();
        }
    }
    pack_writer = std::fopen(pack_path.string().c_str(), "ab");
    if (!pack_writer) {
        std::printf("Shader cache: the pack %s cannot be written; nothing new is kept this run\n",
                    pack_path.string().c_str());
        return;
    }
    u32 imported = 0;
    std::error_code ec;
    std::vector<std::filesystem::path> loose;
    for (const auto& entry : std::filesystem::directory_iterator(folder, ec)) {
        const auto ext = entry.path().extension().string();
        if (entry.is_regular_file(ec) && (ext == ".meta" || ext == ".spv" || ext == ".key" || ext == ".bin")) {
            loose.push_back(entry.path());
        }
    }
    std::vector<u8> data;
    for (const auto& path : loose) {
        std::FILE* f = std::fopen(path.string().c_str(), "rb");
        if (!f) {
            continue;
        }
        const u64 size = std::filesystem::file_size(path, ec);
        data.resize(size);
        const bool read = std::fread(data.data(), 1, size, f) == size;
        std::fclose(f);
        if (!read) {
            continue;
        }
        const std::string key = path.filename().string();
        const u64 hash = XXH3_64bits(data.data(), data.size());
        const u64 at = PackAppend(key, 0, data.data(), u32(data.size()), hash);
        if (at == ~0ull) {
            break;
        }
        {
            std::scoped_lock lk{pack_mutex};
            pack_index[key] = {at, u32(data.size()), hash};
        }
        std::filesystem::remove(path, ec);
        ++imported;
    }
    if (imported) {
        std::printf("Shader cache: %u loose files moved into the pack\n", imported);
    }
}

constexpr std::string GetBlobFileExtension(BlobType type) {
    switch (type) {
    case BlobType::ShaderMeta: {
        return "meta";
    }
    case BlobType::ShaderBinary: {
        return "spv";
    }
    case BlobType::PipelineKey: {
        return "key";
    }
    case BlobType::ShaderProfile: {
        return "bin";
    }
    default:
        UNREACHABLE();
    }
}

void DataBase::Open() {
    if (opened) {
        return;
    }

    const auto& game_info = Common::ElfInfo::Instance();

    using namespace Common::FS;
    // Offline perf build (feature/native-batch): its own cache. Its shader profile differs from
    // the release builds', so sharing one cache made each build clear the other's at every start.
    // El Dorado: each game of the collection its own folder (all three share the serial CUSA02320: one folder of
    // 33k files that every game listed, and a profile change of one cleared the other two). "-eboot", "-big2",
    // "-big3" from BB_EXE (run.py sets the executable's name).
    std::string game_suffix;
    if (const char* exe = std::getenv("BB_EXE"); exe && *exe) {
        for (const char* c = exe; *c && *c != '.' && *c != '-'; ++c) {
            if (std::isalnum(static_cast<unsigned char>(*c))) {
                game_suffix += *c;
            }
        }
        if (!game_suffix.empty()) {
            game_suffix = "-" + game_suffix;
        }
    }
    const std::string perf_suffix = "-perf" + game_suffix;
    if (EmulatorSettings.IsPipelineCacheArchived()) {
        mz_zip_zero_struct(&zip_ar);

        cache_path = GetUserPath(PathType::CacheDir) /
                     std::filesystem::path{std::string{game_info.GameSerial()} + BbNanGuard::ShaderCacheSuffix() + perf_suffix}.replace_extension(".zip");

        if (!mz_zip_reader_init_file(&zip_ar, cache_path.string().c_str(),
                                     MZ_ZIP_FLAG_READ_ALLOW_WRITING) ||
            !mz_zip_validate_archive(&zip_ar, 0)) {
            LOG_INFO(Render, "Cache archive {} is not found or archive is corrupted",
                     cache_path.string().c_str());
            mz_zip_reader_end(&zip_ar);
            mz_zip_writer_init_file(&zip_ar, cache_path.string().c_str(), 0);
        }
    } else {
        cache_path = GetUserPath(PathType::CacheDir) /
                     (std::string{game_info.GameSerial()} + BbNanGuard::ShaderCacheSuffix() + perf_suffix);
        if (!std::filesystem::exists(cache_path)) {
            std::filesystem::create_directories(cache_path);
        }
        // The old shared folder (before the per-game ones): removed in the background, nothing reads it now.
        if (!game_suffix.empty()) {
            const auto shared = GetUserPath(PathType::CacheDir) /
                                (std::string{game_info.GameSerial()} + BbNanGuard::ShaderCacheSuffix() + "-perf");
            std::error_code ec;
            if (std::filesystem::is_directory(shared, ec)) {
                const auto aside = std::filesystem::path{shared}.concat(".removing");
                std::filesystem::rename(shared, aside, ec);
                if (!ec) {
                    std::printf("Shader cache: the folder shared by the three games is removed (each has its own)\n");
                    std::thread([aside] {
                        std::error_code ignored;
                        std::filesystem::remove_all(aside, ignored);
                    }).detach();
                }
            }
        }
        directory = cache_path;
        if (UsePack()) {
            OpenPack(cache_path);
        }
    }

    const u32 workers = EmulatorSettings.IsPipelineCacheArchived() ? 1 : IoWorkers;
    for (u32 i = 0; i < workers; ++i) {
        io_workers[i] = std::jthread{[i](std::stop_token stoken) { ProcessIO(stoken, i); }};
    }
    opened = true;
}

void DataBase::Close() {
    if (!IsOpened()) {
        return;
    }

    for (auto& worker : io_workers) {
        if (worker.joinable()) {
            worker.request_stop();
            worker.join();
        }
    }

    if (EmulatorSettings.IsPipelineCacheArchived()) {
        mz_zip_writer_finalize_archive(&zip_ar);
        mz_zip_writer_end(&zip_ar);
    }
    if (pack_writer) {
        std::fclose(pack_writer);
        pack_writer = nullptr;
    }

    opened = false;
    LOG_INFO(Render, "Cache dumped");
}

template <typename T>
bool WriteVector(const BlobType type, std::filesystem::path&& path_, std::vector<T>&& v) {
    {
        auto request = std::packaged_task<void()>{[=]() {
            auto path{path_};
            path.replace_extension(GetBlobFileExtension(type));
            if (EmulatorSettings.IsPipelineCacheArchived()) {
                ASSERT_MSG(!ar_is_read_only,
                           "The archive is read-only. Did you forget to call `FinishPreload`?");
                if (!mz_zip_writer_add_mem(&zip_ar, path.string().c_str(), v.data(),
                                           v.size() * sizeof(T), MZ_BEST_COMPRESSION)) {
                    LOG_ERROR(Render, "Failed to add {} to the archive", path.string().c_str());
                }
            } else {
                // bbport: write beside and rename into place, so a game that ends during the
                // write (the queue is not drained at exit) never leaves a truncated blob that
                // the next start would load.
                using namespace Common::FS;
                auto temp{path};
                temp += ".tmp";
                {
                    const auto file = IOFile{temp, FileAccessMode::Create};
                    if (!file.IsOpen() || file.Write(v) != v.size()) {
                        return;
                    }
                }
                // bbport: Windows refuses to replace a file another thread has open (the preload
                // reads it): retry briefly instead of keeping the old file beside the new one of
                // the shader's other half (the meta checksum catches a pair that still differs).
                std::error_code error;
                for (int attempt = 0; attempt < 20; ++attempt) {
                    std::filesystem::rename(temp, path, error);
                    if (!error) {
                        break;
                    }
                    std::this_thread::sleep_for(std::chrono::milliseconds(5));
                }
                if (error) {
                    LOG_WARNING(Render, "Cache file {} not replaced: {}", path.string(),
                                error.message());
                    std::filesystem::remove(temp, error);
                }
            }
        }};
        auto queued{path_};
        queued.replace_extension(GetBlobFileExtension(type));
        Enqueue(queued, std::move(request));
    }
    return true;
}

template <typename T>
void LoadVector(BlobType type, std::filesystem::path& path, std::vector<T>& v) {
    using namespace Common::FS;
    path.replace_extension(GetBlobFileExtension(type));
    if (EmulatorSettings.IsPipelineCacheArchived()) {
        int index{-1};
        index = mz_zip_reader_locate_file(&zip_ar, path.string().c_str(), nullptr, 0);
        if (index < 0) {
            LOG_WARNING(Render, "File {} is not found in the archive", path.string().c_str());
            return;
        }
        mz_zip_archive_file_stat stat{};
        mz_zip_reader_file_stat(&zip_ar, index, &stat);
        v.resize(stat.m_uncomp_size / sizeof(T));
        mz_zip_reader_extract_to_mem(&zip_ar, index, v.data(), stat.m_uncomp_size, 0);
    } else {
        const auto file = IOFile{path, FileAccessMode::Read};
        v.resize(file.GetSize() / sizeof(T));
        file.Read(v);
    }
}

template <typename T>
void PackSave(BlobType type, const std::string& name, std::vector<T>&& v) {
    const std::string key = name + "." + GetBlobFileExtension(type);
    auto request = std::packaged_task<void()>{[key, v = std::move(v)]() {
        const u32 size = u32(v.size() * sizeof(T));
        const u64 hash = XXH3_64bits(v.data(), size);
        const u64 at = PackAppend(key, 0, v.data(), size, hash);
        if (at == ~0ull) {
            return;
        }
        std::scoped_lock lk{pack_mutex};
        if (const auto it = pack_index.find(key); it != pack_index.end()) {
            pack_dead += sizeof(PackHeader) + key.size() + it->second.size;
        }
        pack_index[key] = {at, size, hash};
    }};
    Enqueue(pack_path, std::move(request));
}

template <typename T>
void PackLoad(BlobType type, const std::string& name, std::vector<T>& v) {
    v.clear();
    PackEntry entry;
    {
        std::scoped_lock lk{pack_mutex};
        const auto it = pack_index.find(name + "." + GetBlobFileExtension(type));
        if (it == pack_index.end()) {
            return; // not stored: no error (a first preparation asks for every stage)
        }
        entry = it->second;
    }
    std::vector<u8> bytes(entry.size);
    if (!PackRead(entry, bytes.data())) {
        std::printf("Shader cache: %s.%s in the pack does not read back whole; it is made again\n", name.c_str(),
                    GetBlobFileExtension(type).c_str());
        return;
    }
    v.resize(entry.size / sizeof(T));
    std::memcpy(v.data(), bytes.data(), v.size() * sizeof(T));
}

bool DataBase::Save(BlobType type, const std::string& name, std::vector<u8>&& data) {
    if (!opened) {
        return false;
    }
    if (pack_mode) {
        PackSave(type, name, std::move(data));
        return true;
    }

    auto path = EmulatorSettings.IsPipelineCacheArchived() ? std::filesystem::path{name}
                                                           : cache_path / name;
    return WriteVector(type, std::move(path), std::move(data));
}

bool DataBase::Save(BlobType type, const std::string& name, std::vector<u32>&& data) {
    if (!opened) {
        return false;
    }
    if (pack_mode) {
        PackSave(type, name, std::move(data));
        return true;
    }

    auto path = EmulatorSettings.IsPipelineCacheArchived() ? std::filesystem::path{name}
                                                           : cache_path / name;
    return WriteVector(type, std::move(path), std::move(data));
}

void DataBase::Load(BlobType type, const std::string& name, std::vector<u8>& data) {
    if (!opened) {
        return;
    }
    if (pack_mode) {
        return PackLoad(type, name, data);
    }

    auto path = EmulatorSettings.IsPipelineCacheArchived() ? std::filesystem::path{name}
                                                           : cache_path / name;
    return LoadVector(type, path, data);
}

void DataBase::Load(BlobType type, const std::string& name, std::vector<u32>& data) {
    if (!opened) {
        return;
    }
    if (pack_mode) {
        return PackLoad(type, name, data);
    }

    auto path = EmulatorSettings.IsPipelineCacheArchived() ? std::filesystem::path{name}
                                                           : cache_path / name;
    return LoadVector(type, path, data);
}

void DataBase::ForEachBlob(BlobType type, const std::function<void(std::vector<u8>&& data)>& func) {
    const auto& ext = GetBlobFileExtension(type);
    if (pack_mode) {
        for (const auto& name : ListBlobNames(type)) {
            std::vector<u8> data;
            PackLoad(type, name, data);
            if (!data.empty()) {
                func(std::move(data));
            }
        }
        return;
    }
    if (EmulatorSettings.IsPipelineCacheArchived()) {
        const auto num_files = mz_zip_reader_get_num_files(&zip_ar);
        for (int index = 0; index < num_files; ++index) {
            std::array<char, MZ_ZIP_MAX_ARCHIVE_FILENAME_SIZE> file_name{};
            file_name.fill(0);
            mz_zip_reader_get_filename(&zip_ar, index, file_name.data(), file_name.size());
            if (std::string{file_name.data()}.ends_with(ext)) {
                mz_zip_archive_file_stat stat{};
                mz_zip_reader_file_stat(&zip_ar, index, &stat);
                std::vector<u8> data(stat.m_uncomp_size);
                mz_zip_reader_extract_to_mem(&zip_ar, index, data.data(), data.size(), 0);
                func(std::move(data));
            }
        }
    } else {
        for (const auto& file_name : std::filesystem::directory_iterator{cache_path}) {
            if (file_name.path().extension().string().ends_with(ext)) {
                using namespace Common::FS;
                const auto& file = IOFile{file_name, FileAccessMode::Read};
                if (file.IsOpen()) {
                    std::vector<u8> data(file.GetSize());
                    file.Read(data);
                    func(std::move(data));
                }
            }
        }
    }
}

std::vector<std::string> DataBase::ListBlobNames(BlobType type) {
    std::vector<std::string> names;
    if (!opened) {
        return names;
    }
    const auto ext = "." + GetBlobFileExtension(type);
    if (pack_mode) {
        std::scoped_lock lk{pack_mutex};
        for (const auto& [key, entry] : pack_index) {
            if (key.ends_with(ext)) {
                names.push_back(key.substr(0, key.size() - ext.size()));
            }
        }
        return names;
    }
    if (EmulatorSettings.IsPipelineCacheArchived()) {
        const auto num_files = mz_zip_reader_get_num_files(&zip_ar);
        for (int index = 0; index < num_files; ++index) {
            std::array<char, MZ_ZIP_MAX_ARCHIVE_FILENAME_SIZE> file_name{};
            mz_zip_reader_get_filename(&zip_ar, index, file_name.data(), file_name.size());
            const std::string entry{file_name.data()};
            if (entry.ends_with(ext)) {
                names.push_back(entry.substr(0, entry.size() - ext.size()));
            }
        }
        return names;
    }
    std::error_code ec;
    for (const auto& entry : std::filesystem::directory_iterator(cache_path, ec)) {
        if (entry.path().extension().string() == ext) {
            names.push_back(entry.path().stem().string());
        }
    }
    return names;
}

u32 DataBase::PendingWrites() const {
    return num_requests.load();
}

void DataBase::Flush(u32 max_ms) {
    const auto end = std::chrono::steady_clock::now() + std::chrono::milliseconds(max_ms);
    while (opened && num_requests.load() != 0 && std::chrono::steady_clock::now() < end) {
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
}

void DataBase::Clear() {
    if (!opened || EmulatorSettings.IsPipelineCacheArchived()) {
        return;
    }
    std::error_code ec;
    u64 removed = 0;
    if (pack_mode) {
        Flush(10000);
        std::scoped_lock lk{pack_mutex};
        removed = pack_index.size();
        pack_index.clear();
        pack_end = pack_dead = 0;
        if (pack_writer) {
            std::fclose(pack_writer);
        }
        pack_generation.fetch_add(1, std::memory_order_acq_rel);
        if (std::FILE* f = std::fopen(pack_path.string().c_str(), "wb")) {
            std::fclose(f);
        }
        pack_writer = std::fopen(pack_path.string().c_str(), "ab");
    }
    for (const auto& entry : std::filesystem::directory_iterator(cache_path, ec)) {
        if (entry.is_regular_file(ec) && entry.path() != pack_path && std::filesystem::remove(entry.path(), ec)) {
            ++removed;
        }
    }
    LOG_WARNING(Render, "Pipeline cache cleared ({} files): it is rebuilt for this build", removed);
}

void DataBase::Remove(BlobType type, const std::string& name) {
    if (!opened || EmulatorSettings.IsPipelineCacheArchived()) {
        return;
    }
    if (pack_mode) {
        const std::string key = name + "." + GetBlobFileExtension(type);
        auto request = std::packaged_task<void()>{[key]() {
            {
                std::scoped_lock lk{pack_mutex};
                const auto it = pack_index.find(key);
                if (it == pack_index.end()) {
                    return;
                }
                pack_dead += 2 * sizeof(PackHeader) + 2 * key.size() + it->second.size;
                pack_index.erase(it);
            }
            PackAppend(key, 1, nullptr, 0, 0);
        }};
        Enqueue(pack_path, std::move(request));
        return;
    }
    auto path = cache_path / name;
    path.replace_extension(GetBlobFileExtension(type));
    {
        auto request = std::packaged_task<void()>{[path]() {
            std::error_code error;
            std::filesystem::remove(path, error);
        }};
        Enqueue(path, std::move(request));
    }
}

void DataBase::FinishPreload() {
    if (EmulatorSettings.IsPipelineCacheArchived()) {
        mz_zip_writer_init_from_reader(&zip_ar, cache_path.string().c_str());
        ar_is_read_only = false;
    }
}

} // namespace Storage
