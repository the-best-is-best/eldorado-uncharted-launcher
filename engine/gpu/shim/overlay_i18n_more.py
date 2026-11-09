# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
# The in-game menu in the launcher's other languages (besides the six in overlay_i18n.py and Arabic).
# Wording follows the launcher's (launcher/ui/i18n/<code>.json), including its form of "you": informal in nl, da, no,
# sv, fi and pl, polite in cs, el, ru and tr. Checkpoint names and chapter titles are the games' own and stay English.

LANGUAGES = ('nl', 'da', 'no', 'sv', 'fi', 'pl', 'cs', 'el', 'ru', 'tr')


def R(nl, da, no, sv, fi, pl, cs, el, ru, tr):
    return dict(zip(LANGUAGES, (nl, da, no, sv, fi, pl, cs, el, ru, tr)))


MENU = {
    # ---- Render size labels ----------------------------------------------------------------------------------------
    "(the game's own)": R(
        '(van de game)', '(spillets egen)', '(spillets egen)', '(spelets egen)', '(pelin oma)', '(własna gry)',
        '(vlastní hry)', '(του παιχνιδιού)', '(как в игре)', '(oyunun kendi)'),
    '(native)': R(
        '(native)', '(native)', '(native)', '(native)', '(natiivi)', '(natywna)', '(nativní)', '(εγγενής)',
        '(родное)', '(yerel)'),
    '(Quality)': R(
        '(Kwaliteit)', '(Kvalitet)', '(Kvalitet)', '(Kvalitet)', '(Laatu)', '(Jakość)', '(Kvalita)', '(Ποιότητα)',
        '(Качество)', '(Kalite)'),
    '(Balanced)': R(
        '(Gebalanceerd)', '(Balanceret)', '(Balansert)', '(Balanserad)', '(Tasapainoinen)', '(Zrównoważona)',
        '(Vyvážený)', '(Ισορροπημένο)', '(Баланс)', '(Dengeli)'),
    '(Performance)': R(
        '(Prestaties)', '(Ydeevne)', '(Ytelse)', '(Prestanda)', '(Suorituskyky)', '(Wydajność)', '(Výkon)',
        '(Επιδόσεις)', '(Производительность)', '(Performans)'),

    # ---- Checkpoints page ------------------------------------------------------------------------------------------
    'Done.': R('Klaar.', 'Færdig.', 'Ferdig.', 'Klart.', 'Valmis.', 'Gotowe.', 'Hotovo.', 'Έγινε.', 'Готово.',
               'Tamamlandı.'),
    'This checkpoint is not in this release of the game.': R(
        'Dit checkpoint zit niet in deze versie van de game.',
        'Dette checkpoint findes ikke i denne udgave af spillet.',
        'Dette sjekkpunktet finnes ikke i denne utgaven av spillet.',
        'Den här kontrollpunkten finns inte i den här versionen av spelet.',
        'Tätä tarkistuspistettä ei ole tässä peliversiossa.',
        'Tego punktu kontrolnego nie ma w tej wersji gry.',
        'Tento kontrolní bod v této verzi hry není.',
        'Αυτό το σημείο ελέγχου δεν υπάρχει σε αυτή την έκδοση του παιχνιδιού.',
        'Этой контрольной точки нет в этой версии игры.',
        'Bu kontrol noktası oyunun bu sürümünde yok.'),
    'Checkpoint jumps do not work with this release of the game.': R(
        'Sprongen naar checkpoints werken niet met deze versie van de game.',
        'Spring til checkpoints virker ikke med denne udgave af spillet.',
        'Hopp til sjekkpunkter virker ikke med denne utgaven av spillet.',
        'Hopp till kontrollpunkter fungerar inte med den här versionen av spelet.',
        'Tarkistuspisteisiin hyppääminen ei toimi tässä peliversiossa.',
        'Skoki do punktów kontrolnych nie działają w tej wersji gry.',
        'Skoky na kontrolní body s touto verzí hry nefungují.',
        'Τα άλματα σε σημεία ελέγχου δεν λειτουργούν σε αυτή την έκδοση του παιχνιδιού.',
        'Переходы к контрольным точкам не работают в этой версии игры.',
        'Kontrol noktasına atlama oyunun bu sürümünde çalışmıyor.'),
    'Now: %s': R('Nu: %s', 'Nu: %s', 'Nå: %s', 'Nu: %s', 'Nyt: %s', 'Teraz: %s', 'Nyní: %s', 'Τώρα: %s',
                 'Сейчас: %s', 'Şu an: %s'),
    'Checkpoint jumps are not available for this release of the game.': R(
        'Sprongen naar checkpoints zijn niet beschikbaar voor deze versie van de game.',
        'Spring til checkpoints findes ikke til denne udgave af spillet.',
        'Hopp til sjekkpunkter er ikke tilgjengelig for denne utgaven av spillet.',
        'Hopp till kontrollpunkter är inte tillgängliga för den här versionen av spelet.',
        'Tarkistuspisteisiin hyppääminen ei ole käytettävissä tässä peliversiossa.',
        'Skoki do punktów kontrolnych nie są dostępne w tej wersji gry.',
        'Skoky na kontrolní body nejsou pro tuto verzi hry k dispozici.',
        'Τα άλματα σε σημεία ελέγχου δεν είναι διαθέσιμα για αυτή την έκδοση του παιχνιδιού.',
        'Переходы к контрольным точкам недоступны для этой версии игры.',
        'Kontrol noktasına atlama oyunun bu sürümü için kullanılamıyor.'),
    'Practice mode: the game saves to a practice copy until you restart it. Your own save and story save are not '
    'touched.': R(
        'Oefenmodus: de game slaat op in een oefenkopie tot je hem opnieuw start. Je eigen opslag en verhaalopslag '
        'blijven onaangeroerd.',
        'Øvetilstand: spillet gemmer i en øvekopi, indtil du genstarter det. Din egen gemning og historiegemning '
        'røres ikke.',
        'Øvingsmodus: spillet lagrer i en øvingskopi til du starter det på nytt. Din egen lagring og historielagring '
        'røres ikke.',
        'Övningsläge: spelet sparar i en övningskopia tills du startar om det. Din egen sparfil och '
        'berättelsesparfil rörs inte.',
        'Harjoitustila: peli tallentaa harjoituskopioon, kunnes käynnistät sen uudelleen. Omaan tallennukseesi ja '
        'tarinatallennukseen ei kosketa.',
        'Tryb treningowy: gra zapisuje do kopii treningowej, dopóki jej nie uruchomisz ponownie. Twój zapis i zapis '
        'fabularny pozostają nietknięte.',
        'Tréninkový režim: hra ukládá do tréninkové kopie, dokud ji nerestartujete. Vaše vlastní pozice a příběhová '
        'pozice zůstanou nedotčené.',
        'Λειτουργία εξάσκησης: το παιχνίδι αποθηκεύει σε αντίγραφο εξάσκησης μέχρι να το επανεκκινήσετε. Η δική σας '
        'αποθήκευση και η αποθήκευση ιστορίας δεν αγγίζονται.',
        'Режим тренировки: игра сохраняется в тренировочную копию, пока вы её не перезапустите. Ваше сохранение и '
        'сюжетное сохранение не затрагиваются.',
        'Alıştırma modu: oyun, siz yeniden başlatana kadar bir alıştırma kopyasına kaydeder. Kendi kaydınız ve hikâye '
        'kaydınız etkilenmez.'),
    'Keep this progress': R(
        'Deze voortgang houden', 'Behold dette fremskridt', 'Behold denne fremgangen', 'Behåll de här framstegen',
        'Säilytä tämä edistyminen', 'Zachowaj ten postęp', 'Ponechat tento postup', 'Διατήρηση αυτής της προόδου',
        'Сохранить этот прогресс', 'Bu ilerlemeyi koru'),
    'To carry on from here for real (for example past a place that does not work): the game restarts and Continue '
    'starts at the practice save, which becomes your save and your story save. Your save from before is kept in Save '
    'slots as "Before the last load".': R(
        'Om echt vanaf hier verder te spelen (bijvoorbeeld voorbij een plek die niet werkt): de game start opnieuw en '
        'Doorgaan begint bij de oefenopslag, die je opslag en je verhaalopslag wordt. Je vorige opslag blijft bewaard '
        'in Opslagslots als "Vóór het laatste laden".',
        'For at fortsætte herfra for alvor (fx forbi et sted, der ikke virker): spillet genstarter, og Fortsæt '
        'starter ved øvegemningen, som bliver din gemning og din historiegemning. Din tidligere gemning gemmes under '
        'Gemmepladser som "Før sidste indlæsning".',
        'For å fortsette herfra på ekte (f.eks. forbi et sted som ikke virker): spillet starter på nytt, og Fortsett '
        'starter ved øvingslagringen, som blir din lagring og din historielagring. Den forrige lagringen din beholdes '
        'under Lagringsplasser som "Før siste innlasting".',
        'För att fortsätta härifrån på riktigt (t.ex. förbi ett ställe som inte fungerar): spelet startar om och '
        'Fortsätt börjar vid övningssparfilen, som blir din sparfil och din berättelsesparfil. Din tidigare sparfil '
        'behålls under Sparplatser som "Före senaste inläsningen".',
        'Jatkaaksesi tästä oikeasti (esimerkiksi kohdan ohi, joka ei toimi): peli käynnistyy uudelleen ja Jatka alkaa '
        'harjoitustallennuksesta, josta tulee tallennuksesi ja tarinatallennuksesi. Aiempi tallennuksesi säilyy '
        'Tallennuspaikoissa nimellä "Ennen viimeisintä latausta".',
        'Aby naprawdę grać dalej stąd (np. za miejscem, które nie działa): gra uruchomi się ponownie, a Kontynuuj '
        'zacznie od zapisu treningowego, który stanie się twoim zapisem i zapisem fabularnym. Twój wcześniejszy zapis '
        'zostanie w Slotach zapisu jako "Przed ostatnim wczytaniem".',
        'Chcete-li odsud doopravdy pokračovat (např. za místem, které nefunguje): hra se restartuje a Pokračovat '
        'začne u tréninkové pozice, která se stane vaší pozicí i příběhovou pozicí. Vaše dřívější pozice zůstane ve '
        'Slotech pozic jako "Před posledním načtením".',
        'Για να συνεχίσετε πραγματικά από εδώ (π.χ. μετά από ένα σημείο που δεν λειτουργεί): το παιχνίδι '
        'επανεκκινείται και η Συνέχεια ξεκινά από την αποθήκευση εξάσκησης, που γίνεται η αποθήκευσή σας και η '
        'αποθήκευση ιστορίας σας. Η προηγούμενη αποθήκευσή σας φυλάσσεται στις Θέσεις αποθήκευσης ως "Πριν την '
        'τελευταία φόρτωση".',
        'Чтобы продолжить отсюда по-настоящему (например, за местом, которое не работает): игра перезапустится, и '
        '"Продолжить" начнёт с тренировочного сохранения, которое станет вашим сохранением и сюжетным сохранением. '
        'Прежнее сохранение останется в слотах сохранений как "До последней загрузки".',
        'Buradan gerçekten devam etmek için (örneğin çalışmayan bir yerin ötesine): oyun yeniden başlar ve Devam, '
        'alıştırma kaydından başlar; bu kayıt sizin kaydınız ve hikâye kaydınız olur. Önceki kaydınız Kayıt '
        'yuvalarında "Son yüklemeden önce" olarak tutulur.'),
    'Make the practice save your save? The game restarts and Continue starts there. Your save from before is kept as '
    '"Before the last load".': R(
        'De oefenopslag je opslag maken? De game start opnieuw en Doorgaan begint daar. Je vorige opslag blijft '
        'bewaard als "Vóór het laatste laden".',
        'Gøre øvegemningen til din gemning? Spillet genstarter, og Fortsæt starter der. Din tidligere gemning gemmes '
        'som "Før sidste indlæsning".',
        'Gjøre øvingslagringen til din lagring? Spillet starter på nytt, og Fortsett starter der. Den forrige '
        'lagringen din beholdes som "Før siste innlasting".',
        'Göra övningssparfilen till din sparfil? Spelet startar om och Fortsätt börjar där. Din tidigare sparfil '
        'behålls som "Före senaste inläsningen".',
        'Tehdäänkö harjoitustallennuksesta tallennuksesi? Peli käynnistyy uudelleen ja Jatka alkaa siitä. Aiempi '
        'tallennuksesi säilyy nimellä "Ennen viimeisintä latausta".',
        'Zrobić z zapisu treningowego twój zapis? Gra uruchomi się ponownie, a Kontynuuj zacznie tam. Twój '
        'wcześniejszy zapis zostanie jako "Przed ostatnim wczytaniem".',
        'Udělat z tréninkové pozice vaši pozici? Hra se restartuje a Pokračovat začne tam. Vaše dřívější pozice '
        'zůstane jako "Před posledním načtením".',
        'Να γίνει η αποθήκευση εξάσκησης η αποθήκευσή σας; Το παιχνίδι επανεκκινείται και η Συνέχεια ξεκινά από εκεί. '
        'Η προηγούμενη αποθήκευσή σας φυλάσσεται ως "Πριν την τελευταία φόρτωση".',
        'Сделать тренировочное сохранение вашим? Игра перезапустится, и "Продолжить" начнёт оттуда. Прежнее '
        'сохранение останется как "До последней загрузки".',
        'Alıştırma kaydı kaydınız yapılsın mı? Oyun yeniden başlar ve Devam oradan başlar. Önceki kaydınız "Son '
        'yüklemeden önce" olarak tutulur.'),
    'Yes, keep it': R(
        'Ja, houden', 'Ja, behold den', 'Ja, behold den', 'Ja, behåll den', 'Kyllä, säilytä', 'Tak, zachowaj',
        'Ano, ponechat', 'Ναι, διατήρηση', 'Да, сохранить', 'Evet, koru'),
    'Cancel': R('Annuleren', 'Annuller', 'Avbryt', 'Avbryt', 'Peruuta', 'Anuluj', 'Zrušit', 'Άκυρο', 'Отмена',
                'İptal'),
    'Jumping turns on practice mode: until the game restarts, it saves to a practice copy, not to your own save.': R(
        'Springen zet de oefenmodus aan: tot de game opnieuw start, slaat hij op in een oefenkopie, niet in je eigen '
        'opslag.',
        'Et spring slår øvetilstand til: indtil spillet genstarter, gemmer det i en øvekopi, ikke i din egen gemning.',
        'Et hopp slår på øvingsmodus: til spillet starter på nytt, lagrer det i en øvingskopi, ikke i din egen '
        'lagring.',
        'Ett hopp slår på övningsläget: tills spelet startar om sparar det i en övningskopia, inte i din egen sparfil.',
        'Hyppy kytkee harjoitustilan päälle: kunnes peli käynnistyy uudelleen, se tallentaa harjoituskopioon, ei '
        'omaan tallennukseesi.',
        'Skok włącza tryb treningowy: do ponownego uruchomienia gra zapisuje do kopii treningowej, nie do twojego '
        'zapisu.',
        'Skok zapne tréninkový režim: do restartu hry se ukládá do tréninkové kopie, ne do vaší vlastní pozice.',
        'Το άλμα ενεργοποιεί τη λειτουργία εξάσκησης: μέχρι την επανεκκίνηση, το παιχνίδι αποθηκεύει σε αντίγραφο '
        'εξάσκησης, όχι στη δική σας αποθήκευση.',
        'Переход включает режим тренировки: до перезапуска игра сохраняется в тренировочную копию, а не в ваше '
        'сохранение.',
        'Atlama alıştırma modunu açar: oyun yeniden başlayana kadar kendi kaydınıza değil, bir alıştırma kopyasına '
        'kaydeder.'),
    'Chapter': R('Hoofdstuk', 'Kapitel', 'Kapittel', 'Kapitel', 'Luku', 'Rozdział', 'Kapitola', 'Κεφάλαιο', 'Глава',
                 'Bölüm'),
    '(now)': R('(nu)', '(nu)', '(nå)', '(nu)', '(nyt)', '(teraz)', '(nyní)', '(τώρα)', '(сейчас)', '(şu an)'),
    'Mouse': R('Muis', 'Mus', 'Mus', 'Mus', 'Hiiri', 'Mysz', 'Myš', 'Ποντίκι', 'Мышь', 'Fare'),
    'Mouse sensitivity': R('Muisgevoeligheid', 'Musens følsomhed', 'Musfølsomhet', 'Muskänslighet', 'Hiiren herkkyys',
                           'Czułość myszy', 'Citlivost myši', 'Ευαισθησία ποντικιού', 'Чувствительность мыши',
                           'Fare hassasiyeti'),
    'Aiming sensitivity': R('Gevoeligheid bij richten', 'Følsomhed ved sigte', 'Følsomhet ved sikting',
                            'Känslighet vid sikte', 'Herkkyys tähdätessä', 'Czułość przy celowaniu',
                            'Citlivost při míření', 'Ευαισθησία στη σκόπευση', 'Чувствительность при прицеливании',
                            'Nişan alırken hassasiyet'),
    'Vertical sensitivity': R('Verticale gevoeligheid', 'Lodret følsomhed', 'Vertikal følsomhet',
                              'Vertikal känslighet', 'Pystysuora herkkyys', 'Czułość pionowa', 'Svislá citlivost',
                              'Κατακόρυφη ευαισθησία', 'Вертикальная чувствительность', 'Dikey hassasiyet'),
    'Aiming: times the mouse sensitivity while aiming (1.00 the same as looking around). Vertical: times it for '
    'up and down. Ctrl+click to type a value.': R(
        'Richten: keer de muisgevoeligheid tijdens het richten (1.00 hetzelfde als rondkijken). Verticaal: keer die '
        'voor omhoog en omlaag. Ctrl+klik om een waarde te typen.',
        'Sigte: gange musens følsomhed under sigte (1.00 det samme som at se sig omkring). Lodret: gange den op og '
        'ned. Ctrl+klik for at skrive en værdi.',
        'Sikting: ganger musfølsomheten mens du sikter (1.00 det samme som å se seg rundt). Vertikal: ganger den '
        'opp og ned. Ctrl+klikk for å skrive inn en verdi.',
        'Sikte: gånger muskänsligheten när du siktar (1.00 samma som att se sig omkring). Vertikal: gånger den upp '
        'och ner. Ctrl+klicka för att skriva ett värde.',
        'Tähtäys: hiiren herkkyyden kerroin tähdätessä (1.00 sama kuin ympärille katsoessa). Pystysuora: kerroin '
        'ylös ja alas. Ctrl+napsautus kirjoittaa arvon.',
        'Celowanie: mnożnik czułości myszy podczas celowania (1.00 tak samo jak przy rozglądaniu się). Pionowa: '
        'mnożnik w górę i w dół. Ctrl+klik, aby wpisać wartość.',
        'Míření: násobek citlivosti myši při míření (1.00 stejně jako při rozhlížení). Svislá: násobek pro pohyb '
        'nahoru a dolů. Ctrl+kliknutím zadáte hodnotu.',
        'Σκόπευση: πολλαπλασιαστής της ευαισθησίας του ποντικιού κατά τη σκόπευση (1.00 ίδια με το να κοιτάς '
        'γύρω). Κατακόρυφη: πολλαπλασιαστής για πάνω και κάτω. Ctrl+κλικ για να πληκτρολογήσεις τιμή.',
        'Прицеливание: множитель чувствительности мыши при прицеливании (1.00 — как при обзоре). Вертикальная: '
        'множитель для движения вверх и вниз. Ctrl+щелчок, чтобы ввести значение.',
        'Nişan: nişan alırken fare hassasiyetinin çarpanı (1.00 etrafa bakarkenkiyle aynı). Dikey: yukarı ve aşağı '
        'için çarpanı. Değer yazmak için Ctrl+tıklayın.'),
    'Or double-click a checkpoint in the list.': R(
        'Of dubbelklik op een checkpoint in de lijst.', 'Eller dobbeltklik på et checkpoint på listen.',
        'Eller dobbeltklikk på et sjekkpunkt i listen.', 'Eller dubbelklicka på en kontrollpunkt i listan.',
        'Tai kaksoisnapsauta tarkistuspistettä luettelossa.', 'Lub kliknij dwukrotnie punkt kontrolny na liście.',
        'Nebo dvakrát klikněte na kontrolní bod v seznamu.', 'Ή κάνε διπλό κλικ σε ένα σημείο ελέγχου στη λίστα.',
        'Или дважды щёлкните контрольную точку в списке.', 'Ya da listedeki bir kontrol noktasına çift tıklayın.'),
    'Go there': R('Ga erheen', 'Gå dertil', 'Gå dit', 'Gå dit', 'Siirry', 'Przejdź', 'Přejít', 'Μετάβαση',
                  'Перейти', 'Oraya git'),
    "Starts with a movie: use Chapter Select in the game's menu.": R(
        'Begint met een filmpje: gebruik Hoofdstukselectie in het menu van de game.',
        'Starter med en film: brug kapitelvalget i spillets menu.',
        'Starter med en film: bruk kapittelvalget i spillets meny.',
        'Börjar med en film: använd kapitelval i spelets meny.',
        'Alkaa videolla: käytä lukujen valintaa pelin valikossa.',
        'Zaczyna się filmem: użyj wyboru rozdziałów w menu gry.',
        'Začíná videem: použijte výběr kapitol v nabídce hry.',
        'Ξεκινά με βίντεο: χρησιμοποιήστε την Επιλογή κεφαλαίου στο μενού του παιχνιδιού.',
        'Начинается с ролика: используйте выбор глав в меню игры.',
        "Bir videoyla başlar: oyunun menüsündeki Bölüm Seçimi'ni kullanın."),

    # ---- Save slots page -------------------------------------------------------------------------------------------
    'Story save': R(
        'Verhaalopslag', 'Historiegemning', 'Historielagring', 'Berättelsesparfil', 'Tarinatallennus',
        'Zapis fabularny', 'Příběhová pozice', 'Αποθήκευση ιστορίας', 'Сюжетное сохранение', 'Hikâye kaydı'),
    "Starts with the game's next save.": R(
        'Begint bij de volgende opslag van de game.',
        'Starter med spillets næste gemning.',
        'Starter med spillets neste lagring.',
        'Börjar med spelets nästa sparning.',
        'Alkaa pelin seuraavasta tallennuksesta.',
        'Zaczyna się od następnego zapisu gry.',
        'Začne dalším uložením hry.',
        'Ξεκινά με την επόμενη αποθήκευση του παιχνιδιού.',
        'Начнётся со следующего сохранения игры.',
        'Oyunun bir sonraki kaydıyla başlar.'),
    'Your save has moved away from your story (Chapter Select or a new game). The story save stays here until you '
    'load it, or make the current save your story save to keep the change.': R(
        'Je opslag is afgeweken van je verhaal (Hoofdstukselectie of een nieuwe game). De verhaalopslag blijft hier '
        'tot je hem laadt, of maak de huidige opslag je verhaalopslag om de wijziging te houden.',
        'Din gemning er kommet væk fra din historie (kapitelvalg eller et nyt spil). Historiegemningen bliver her, '
        'indtil du indlæser den, eller gør den nuværende gemning til din historiegemning for at beholde ændringen.',
        'Lagringen din har beveget seg bort fra historien din (kapittelvalg eller et nytt spill). Historielagringen '
        'blir her til du laster den inn, eller gjør den nåværende lagringen til historielagringen din for å beholde '
        'endringen.',
        'Din sparfil har lämnat din berättelse (kapitelval eller ett nytt spel). Berättelsesparfilen stannar här tills '
        'du läser in den, eller gör den nuvarande sparfilen till din berättelsesparfil för att behålla ändringen.',
        'Tallennuksesi on siirtynyt pois tarinastasi (lukujen valinta tai uusi peli). Tarinatallennus pysyy tässä, '
        'kunnes lataat sen, tai tee nykyisestä tallennuksesta tarinatallennuksesi säilyttääksesi muutoksen.',
        'Twój zapis odszedł od twojej fabuły (wybór rozdziałów lub nowa gra). Zapis fabularny zostaje tu, dopóki go '
        'nie wczytasz, albo zrób z obecnego zapisu zapis fabularny, aby zachować zmianę.',
        'Vaše pozice se vzdálila od vašeho příběhu (výběr kapitol nebo nová hra). Příběhová pozice tu zůstane, dokud '
        'ji nenačtete, nebo z aktuální pozice udělejte příběhovou, abyste změnu zachovali.',
        'Η αποθήκευσή σας απομακρύνθηκε από την ιστορία σας (Επιλογή κεφαλαίου ή νέο παιχνίδι). Η αποθήκευση '
        'ιστορίας μένει εδώ μέχρι να τη φορτώσετε, ή κάντε την τρέχουσα αποθήκευση αποθήκευση ιστορίας για να '
        'κρατήσετε την αλλαγή.',
        'Ваше сохранение ушло от вашего сюжета (выбор глав или новая игра). Сюжетное сохранение остаётся здесь, пока '
        'вы его не загрузите, или сделайте текущее сохранение сюжетным, чтобы оставить изменение.',
        "Kaydınız hikâyenizden ayrıldı (Bölüm Seçimi veya yeni oyun). Hikâye kaydı siz yükleyene kadar burada kalır; "
        "değişikliği korumak için mevcut kaydı hikâye kaydınız yapın."),
    'Follows your playthrough as you play on.': R(
        'Volgt je playthrough terwijl je verder speelt.',
        'Følger dit gennemspil, mens du spiller videre.',
        'Følger gjennomspillingen din mens du spiller videre.',
        'Följer din genomspelning medan du spelar vidare.',
        'Seuraa pelikertaasi, kun pelaat eteenpäin.',
        'Podąża za twoją rozgrywką, gdy grasz dalej.',
        'Sleduje váš průchod hrou, jak hrajete dál.',
        'Ακολουθεί την πορεία σας στο παιχνίδι καθώς συνεχίζετε.',
        'Следует за вашим прохождением, пока вы играете дальше.',
        'Siz oynadıkça oyun ilerlemenizi takip eder.'),
    'Load story save': R(
        'Verhaalopslag laden', 'Indlæs historiegemning', 'Last inn historielagring', 'Läs in berättelsesparfil',
        'Lataa tarinatallennus', 'Wczytaj zapis fabularny', 'Načíst příběhovou pozici', 'Φόρτωση αποθήκευσης ιστορίας',
        'Загрузить сюжетное сохранение', 'Hikâye kaydını yükle'),
    'Make this my story save': R(
        'Maak dit mijn verhaalopslag', 'Gør dette til min historiegemning', 'Gjør dette til historielagringen min',
        'Gör detta till min berättelsesparfil', 'Tee tästä tarinatallennukseni', 'Ustaw jako mój zapis fabularny',
        'Nastavit jako příběhovou pozici', 'Ορισμός ως αποθήκευση ιστορίας', 'Сделать сюжетным сохранением',
        'Bunu hikâye kaydım yap'),
    'Use this after skipping ahead on purpose: the story save then follows your playthrough from where you are now.': R(
        'Gebruik dit nadat je bewust vooruit bent gesprongen: de verhaalopslag volgt je playthrough dan vanaf waar je '
        'nu bent.',
        'Brug dette, når du med vilje er sprunget frem: historiegemningen følger så dit gennemspil fra der, hvor du er '
        'nu.',
        'Bruk dette etter å ha hoppet fremover med vilje: historielagringen følger da gjennomspillingen din fra der du '
        'er nå.',
        'Använd detta efter att du hoppat framåt med flit: berättelsesparfilen följer då din genomspelning från där du '
        'är nu.',
        'Käytä tätä, kun olet hypännyt tarkoituksella eteenpäin: tarinatallennus seuraa sitten pelikertaasi siitä, '
        'missä olet nyt.',
        'Użyj tego po celowym przeskoczeniu do przodu: zapis fabularny będzie wtedy podążał za twoją rozgrywką od '
        'miejsca, w którym jesteś.',
        'Použijte po úmyslném přeskočení dopředu: příběhová pozice pak sleduje váš průchod od místa, kde jste teď.',
        'Χρησιμοποιήστε το αφού προχωρήσετε σκόπιμα μπροστά: η αποθήκευση ιστορίας ακολουθεί τότε την πορεία σας από '
        'εκεί που βρίσκεστε τώρα.',
        'Используйте после намеренного перехода вперёд: сюжетное сохранение будет следовать за прохождением с того '
        'места, где вы сейчас.',
        'Bilerek ileri atladıktan sonra bunu kullanın: hikâye kaydı bundan sonra ilerlemenizi şu anki yerinizden '
        'takip eder.'),
    'Slots': R('Slots', 'Pladser', 'Plasser', 'Platser', 'Paikat', 'Sloty', 'Sloty', 'Θέσεις', 'Слоты', 'Yuvalar'),
    'Save here': R(
        'Hier opslaan', 'Gem her', 'Lagre her', 'Spara här', 'Tallenna tähän', 'Zapisz tutaj', 'Uložit sem',
        'Αποθήκευση εδώ', 'Сохранить сюда', 'Buraya kaydet'),
    'Load': R('Laden', 'Indlæs', 'Last inn', 'Läs in', 'Lataa', 'Wczytaj', 'Načíst', 'Φόρτωση', 'Загрузить',
              'Yükle'),
    'empty': R('leeg', 'tom', 'tom', 'tom', 'tyhjä', 'pusty', 'prázdný', 'κενή', 'пусто', 'boş'),
    'Before the last load: %s%s': R(
        'Vóór het laatste laden: %s%s', 'Før sidste indlæsning: %s%s', 'Før siste innlasting: %s%s',
        'Före senaste inläsningen: %s%s', 'Ennen viimeisintä latausta: %s%s', 'Przed ostatnim wczytaniem: %s%s',
        'Před posledním načtením: %s%s', 'Πριν την τελευταία φόρτωση: %s%s', 'До последней загрузки: %s%s',
        'Son yüklemeden önce: %s%s'),
    'Replace what slot {} holds with your current save?': R(
        'Wat in slot {} staat vervangen door je huidige opslag?',
        'Erstat indholdet af plads {} med din nuværende gemning?',
        'Erstatte innholdet i plass {} med den nåværende lagringen din?',
        'Ersätta innehållet i plats {} med din nuvarande sparfil?',
        'Korvataanko paikan {} sisältö nykyisellä tallennuksellasi?',
        'Zastąpić zawartość slotu {} twoim obecnym zapisem?',
        'Nahradit obsah slotu {} vaší aktuální pozicí?',
        'Αντικατάσταση του περιεχομένου της θέσης {} με την τρέχουσα αποθήκευσή σας;',
        'Заменить содержимое слота {} текущим сохранением?',
        '{}. yuvadakini mevcut kaydınızla değiştirmek istiyor musunuz?'),
    'Load the story save? The game restarts and Continue starts there. Your current save is kept as "Before the last '
    'load".': R(
        'De verhaalopslag laden? De game start opnieuw en Doorgaan begint daar. Je huidige opslag blijft bewaard als '
        '"Vóór het laatste laden".',
        'Indlæse historiegemningen? Spillet genstarter, og Fortsæt starter der. Din nuværende gemning gemmes som '
        '"Før sidste indlæsning".',
        'Laste inn historielagringen? Spillet starter på nytt, og Fortsett starter der. Den nåværende lagringen din '
        'beholdes som "Før siste innlasting".',
        'Läsa in berättelsesparfilen? Spelet startar om och Fortsätt börjar där. Din nuvarande sparfil behålls som '
        '"Före senaste inläsningen".',
        'Ladataanko tarinatallennus? Peli käynnistyy uudelleen ja Jatka alkaa siitä. Nykyinen tallennuksesi säilyy '
        'nimellä "Ennen viimeisintä latausta".',
        'Wczytać zapis fabularny? Gra uruchomi się ponownie, a Kontynuuj zacznie tam. Twój obecny zapis zostanie jako '
        '"Przed ostatnim wczytaniem".',
        'Načíst příběhovou pozici? Hra se restartuje a Pokračovat začne tam. Vaše aktuální pozice zůstane jako "Před '
        'posledním načtením".',
        'Φόρτωση της αποθήκευσης ιστορίας; Το παιχνίδι επανεκκινείται και η Συνέχεια ξεκινά από εκεί. Η τρέχουσα '
        'αποθήκευσή σας φυλάσσεται ως "Πριν την τελευταία φόρτωση".',
        'Загрузить сюжетное сохранение? Игра перезапустится, и "Продолжить" начнёт оттуда. Текущее сохранение '
        'останется как "До последней загрузки".',
        'Hikâye kaydı yüklensin mi? Oyun yeniden başlar ve Devam oradan başlar. Mevcut kaydınız "Son yüklemeden önce" '
        'olarak tutulur.'),
    'Load the save from before the last load? The game restarts and Continue starts there. Your current save is kept '
    'as "Before the last load".': R(
        'De opslag van vóór het laatste laden laden? De game start opnieuw en Doorgaan begint daar. Je huidige opslag '
        'blijft bewaard als "Vóór het laatste laden".',
        'Indlæse gemningen fra før sidste indlæsning? Spillet genstarter, og Fortsæt starter der. Din nuværende '
        'gemning gemmes som "Før sidste indlæsning".',
        'Laste inn lagringen fra før siste innlasting? Spillet starter på nytt, og Fortsett starter der. Den nåværende '
        'lagringen din beholdes som "Før siste innlasting".',
        'Läsa in sparfilen från före senaste inläsningen? Spelet startar om och Fortsätt börjar där. Din nuvarande '
        'sparfil behålls som "Före senaste inläsningen".',
        'Ladataanko tallennus ennen viimeisintä latausta? Peli käynnistyy uudelleen ja Jatka alkaa siitä. Nykyinen '
        'tallennuksesi säilyy nimellä "Ennen viimeisintä latausta".',
        'Wczytać zapis sprzed ostatniego wczytania? Gra uruchomi się ponownie, a Kontynuuj zacznie tam. Twój obecny '
        'zapis zostanie jako "Przed ostatnim wczytaniem".',
        'Načíst pozici z doby před posledním načtením? Hra se restartuje a Pokračovat začne tam. Vaše aktuální pozice '
        'zůstane jako "Před posledním načtením".',
        'Φόρτωση της αποθήκευσης από πριν την τελευταία φόρτωση; Το παιχνίδι επανεκκινείται και η Συνέχεια ξεκινά από '
        'εκεί. Η τρέχουσα αποθήκευσή σας φυλάσσεται ως "Πριν την τελευταία φόρτωση".',
        'Загрузить сохранение до последней загрузки? Игра перезапустится, и "Продолжить" начнёт оттуда. Текущее '
        'сохранение останется как "До последней загрузки".',
        'Son yüklemeden önceki kayıt yüklensin mi? Oyun yeniden başlar ve Devam oradan başlar. Mevcut kaydınız "Son '
        'yüklemeden önce" olarak tutulur.'),
    'Load slot {}? The game restarts and Continue starts there. Your current save is kept as "Before the last '
    'load".': R(
        'Slot {} laden? De game start opnieuw en Doorgaan begint daar. Je huidige opslag blijft bewaard als "Vóór het '
        'laatste laden".',
        'Indlæse plads {}? Spillet genstarter, og Fortsæt starter der. Din nuværende gemning gemmes som "Før sidste '
        'indlæsning".',
        'Laste inn plass {}? Spillet starter på nytt, og Fortsett starter der. Den nåværende lagringen din beholdes '
        'som "Før siste innlasting".',
        'Läsa in plats {}? Spelet startar om och Fortsätt börjar där. Din nuvarande sparfil behålls som "Före senaste '
        'inläsningen".',
        'Ladataanko paikka {}? Peli käynnistyy uudelleen ja Jatka alkaa siitä. Nykyinen tallennuksesi säilyy nimellä '
        '"Ennen viimeisintä latausta".',
        'Wczytać slot {}? Gra uruchomi się ponownie, a Kontynuuj zacznie tam. Twój obecny zapis zostanie jako "Przed '
        'ostatnim wczytaniem".',
        'Načíst slot {}? Hra se restartuje a Pokračovat začne tam. Vaše aktuální pozice zůstane jako "Před posledním '
        'načtením".',
        'Φόρτωση της θέσης {}; Το παιχνίδι επανεκκινείται και η Συνέχεια ξεκινά από εκεί. Η τρέχουσα αποθήκευσή σας '
        'φυλάσσεται ως "Πριν την τελευταία φόρτωση".',
        'Загрузить слот {}? Игра перезапустится, и "Продолжить" начнёт оттуда. Текущее сохранение останется как "До '
        'последней загрузки".',
        '{}. yuva yüklensin mi? Oyun yeniden başlar ve Devam oradan başlar. Mevcut kaydınız "Son yüklemeden önce" '
        'olarak tutulur.'),
    'Make your current save the story save?': R(
        'Je huidige opslag de verhaalopslag maken?',
        'Gøre din nuværende gemning til historiegemningen?',
        'Gjøre den nåværende lagringen din til historielagringen?',
        'Göra din nuvarande sparfil till berättelsesparfilen?',
        'Tehdäänkö nykyisestä tallennuksestasi tarinatallennus?',
        'Zrobić z obecnego zapisu zapis fabularny?',
        'Udělat z aktuální pozice příběhovou pozici?',
        'Να γίνει η τρέχουσα αποθήκευσή σας η αποθήκευση ιστορίας;',
        'Сделать текущее сохранение сюжетным?',
        'Mevcut kaydınız hikâye kaydı yapılsın mı?'),
    'Yes': R('Ja', 'Ja', 'Ja', 'Ja', 'Kyllä', 'Tak', 'Ano', 'Ναι', 'Да', 'Evet'),
    "Copies of this game's campaign save (the one Continue loads). Treasures, unlocks and trophies are not "
    "changed.": R(
        'Kopieën van de campagne-opslag van deze game (die Doorgaan laadt). Schatten, ontgrendelingen en trofeeën '
        'veranderen niet.',
        'Kopier af dette spils kampagnegemning (den, Fortsæt indlæser). Skatte, oplåsninger og trofæer ændres ikke.',
        'Kopier av dette spillets kampanjelagring (den Fortsett laster inn). Skatter, opplåsinger og troféer endres '
        'ikke.',
        'Kopior av spelets kampanjsparfil (den Fortsätt läser in). Skatter, upplåsningar och troféer ändras inte.',
        'Kopioita tämän pelin kampanjatallennuksesta (sen Jatka lataa). Aarteet, avaukset ja palkinnot eivät muutu.',
        'Kopie zapisu kampanii tej gry (tego, który wczytuje Kontynuuj). Skarby, odblokowania i trofea się nie '
        'zmieniają.',
        'Kopie pozice kampaně této hry (té, kterou načítá Pokračovat). Poklady, odemčené položky a trofeje se nemění.',
        'Αντίγραφα της αποθήκευσης εκστρατείας αυτού του παιχνιδιού (αυτής που φορτώνει η Συνέχεια). Θησαυροί, '
        'ξεκλειδώματα και τρόπαια δεν αλλάζουν.',
        'Копии сохранения кампании этой игры (того, что загружает "Продолжить"). Сокровища, открытые бонусы и трофеи '
        'не меняются.',
        'Bu oyunun hikâye kaydının kopyaları (Devam\'ın yüklediği). Hazineler, açılan içerikler ve kupalar '
        'değişmez.'),

    # ---- Settings page ---------------------------------------------------------------------------------------------
    'El Dorado — settings  (Insert / L3+R3)': R(
        'El Dorado — instellingen  (Insert / L3+R3)', 'El Dorado — indstillinger  (Insert / L3+R3)',
        'El Dorado — innstillinger  (Insert / L3+R3)', 'El Dorado — inställningar  (Insert / L3+R3)',
        'El Dorado — asetukset  (Insert / L3+R3)', 'El Dorado — ustawienia  (Insert / L3+R3)',
        'El Dorado — nastavení  (Insert / L3+R3)', 'El Dorado — ρυθμίσεις  (Insert / L3+R3)',
        'El Dorado — настройки  (Insert / L3+R3)', 'El Dorado — ayarlar  (Insert / L3+R3)'),
    '%.0f FPS  (%.1f ms)   1%% low %.0f': R(
        '%.0f FPS  (%.1f ms)   1%% laag %.0f', '%.0f FPS  (%.1f ms)   1%% lav %.0f', '%.0f FPS  (%.1f ms)   1%% lav %.0f',
        '%.0f FPS  (%.1f ms)   1%% låg %.0f', '%.0f FPS  (%.1f ms)   1%% alin %.0f', '%.0f FPS  (%.1f ms)   1%% min. %.0f',
        '%.0f FPS  (%.1f ms)   1%% min. %.0f', '%.0f FPS  (%.1f ms)   1%% χαμηλό %.0f',
        '%.0f FPS  (%.1f ms)   1%% мин. %.0f', '%.0f FPS  (%.1f ms)   %%1 düşük %.0f'),
    "Changes here apply at once, for this session. The launcher's settings apply each time the game starts: set the "
    "same there to keep a change.": R(
        'Wijzigingen hier gelden meteen, voor deze sessie. De instellingen van de launcher gelden bij elke start van '
        'de game: stel daar hetzelfde in om een wijziging te houden.',
        'Ændringer her gælder med det samme, for denne session. Launcherens indstillinger gælder hver gang spillet '
        'starter: vælg det samme der for at beholde en ændring.',
        'Endringer her gjelder med en gang, for denne økten. Launcherens innstillinger gjelder hver gang spillet '
        'starter: velg det samme der for å beholde en endring.',
        'Ändringar här gäller direkt, för den här sessionen. Launcherns inställningar gäller varje gång spelet '
        'startar: ställ in samma sak där för att behålla en ändring.',
        'Muutokset tässä tulevat voimaan heti, tälle istunnolle. Käynnistimen asetukset otetaan käyttöön joka kerta, '
        'kun peli käynnistyy: valitse sama siellä säilyttääksesi muutoksen.',
        'Zmiany tutaj działają od razu, w tej sesji. Ustawienia launchera obowiązują przy każdym uruchomieniu gry: '
        'ustaw to samo tam, aby zachować zmianę.',
        'Změny zde platí hned, pro tuto relaci. Nastavení launcheru platí při každém spuštění hry: nastavte totéž i '
        'tam, chcete-li změnu zachovat.',
        'Οι αλλαγές εδώ ισχύουν αμέσως, για αυτή τη συνεδρία. Οι ρυθμίσεις του launcher ισχύουν σε κάθε εκκίνηση του '
        'παιχνιδιού: ορίστε το ίδιο εκεί για να κρατήσετε μια αλλαγή.',
        'Изменения здесь действуют сразу, в этом сеансе. Настройки лаунчера применяются при каждом запуске игры: '
        'выставьте там то же самое, чтобы сохранить изменение.',
        'Buradaki değişiklikler hemen, bu oturum için geçerli olur. Başlatıcının ayarları oyun her başladığında '
        'uygulanır: bir değişikliği korumak için orada da aynısını ayarlayın.'),
    'Settings': R('Instellingen', 'Indstillinger', 'Innstillinger', 'Inställningar', 'Asetukset', 'Ustawienia',
                  'Nastavení', 'Ρυθμίσεις', 'Настройки', 'Ayarlar'),
    'Picture': R('Beeld', 'Billede', 'Bilde', 'Bild', 'Kuva', 'Obraz', 'Obraz', 'Εικόνα', 'Изображение', 'Görüntü'),
    'Rendering %s': R(
        'Rendering: %s', 'Rendering: %s', 'Rendering: %s', 'Rendering: %s', 'Renderöinti: %s', 'Renderowanie: %s',
        'Vykreslování: %s', 'Απόδοση: %s', 'Рендеринг: %s', 'İşleme: %s'),
    'Set in the launcher (Display: Render resolution); it applies when the game starts. Quality, Balanced and '
    'Performance render smaller and let the anti-aliasing (DLSS or FSR) rebuild the full size: Uncharted 3 only.': R(
        'Ingesteld in de launcher (Beeld: Renderresolutie); geldt bij de start van de game. Kwaliteit, Gebalanceerd '
        'en Prestaties renderen kleiner en laten de anti-aliasing (DLSS of FSR) het volle formaat opbouwen: alleen '
        'Uncharted 3.',
        'Indstilles i launcheren (Skærm: Renderopløsning); gælder når spillet starter. Kvalitet, Balanceret og '
        'Ydeevne renderer mindre og lader kantudjævningen (DLSS eller FSR) genskabe den fulde størrelse: kun '
        'Uncharted 3.',
        'Stilles inn i launcheren (Skjerm: Renderoppløsning); gjelder når spillet starter. Kvalitet, Balansert og '
        'Ytelse rendrer mindre og lar kantutjevningen (DLSS eller FSR) gjenskape full størrelse: bare Uncharted 3.',
        'Ställs in i launchern (Skärm: Renderupplösning); gäller när spelet startar. Kvalitet, Balanserad och '
        'Prestanda renderar mindre och låter kantutjämningen (DLSS eller FSR) återskapa full storlek: bara '
        'Uncharted 3.',
        'Asetetaan käynnistimessä (Näyttö: Renderöintitarkkuus); tulee voimaan pelin käynnistyessä. Laatu, '
        'Tasapainoinen ja Suorituskyky renderöivät pienemmän kuvan, ja reunanpehmennys (DLSS tai FSR) rakentaa täyden '
        'koon: vain Uncharted 3.',
        'Ustawiane w launcherze (Obraz: Rozdzielczość renderowania); działa od uruchomienia gry. Jakość, '
        'Zrównoważona i Wydajność renderują mniejszy obraz, a wygładzanie krawędzi (DLSS lub FSR) odtwarza pełny '
        'rozmiar: tylko Uncharted 3.',
        'Nastavuje se v launcheru (Obraz: Rozlišení vykreslování); platí při spuštění hry. Kvalita, Vyvážený a Výkon '
        'vykreslují menší obraz a vyhlazování hran (DLSS nebo FSR) obnoví plnou velikost: jen Uncharted 3.',
        'Ορίζεται στον launcher (Οθόνη: Ανάλυση απόδοσης)· ισχύει όταν ξεκινά το παιχνίδι. Τα Ποιότητα, '
        'Ισορροπημένο και Επιδόσεις αποδίδουν μικρότερη εικόνα και η εξομάλυνση άκρων (DLSS ή FSR) ανακτά το πλήρες '
        'μέγεθος: μόνο Uncharted 3.',
        'Задаётся в лаунчере (Экран: Разрешение рендеринга); применяется при запуске игры. Качество, Баланс и '
        'Производительность рендерят меньше, а сглаживание (DLSS или FSR) восстанавливает полный размер: только '
        'Uncharted 3.',
        "Başlatıcıda ayarlanır (Görüntü: İşleme çözünürlüğü); oyun başlarken uygulanır. Kalite, Dengeli ve "
        "Performans daha küçük işler ve kenar yumuşatma (DLSS veya FSR) tam boyutu yeniden oluşturur: yalnızca "
        "Uncharted 3."),
    "Off (the game's own)": R(
        'Uit (die van de game)', 'Fra (spillets egen)', 'Av (spillets egen)', 'Av (spelets egen)', 'Pois (pelin oma)',
        'Wył. (własne gry)', 'Vypnuto (vlastní hry)', 'Ανενεργό (του παιχνιδιού)', 'Выкл. (встроенное в игру)',
        'Kapalı (oyunun kendi)'),
    'Anti-aliasing': R(
        'Anti-aliasing', 'Kantudjævning', 'Kantutjevning', 'Kantutjämning', 'Reunanpehmennys', 'Wygładzanie krawędzi',
        'Vyhlazování hran', 'Εξομάλυνση άκρων', 'Сглаживание', 'Kenar yumuşatma'),
    '— not supported by this graphics card': R(
        '— niet ondersteund door deze videokaart', '— understøttes ikke af dette grafikkort',
        '— støttes ikke av dette grafikkortet', '— stöds inte av det här grafikkortet',
        '— tämä näytönohjain ei tue tätä', '— nieobsługiwane przez tę kartę graficzną',
        '— tato grafická karta nepodporuje', '— δεν υποστηρίζεται από αυτή την κάρτα γραφικών',
        '— не поддерживается этой видеокартой', '— bu ekran kartı desteklemiyor'),
    'FSR 4 unavailable: %s': R(
        'FSR 4 niet beschikbaar: %s', 'FSR 4 ikke tilgængelig: %s', 'FSR 4 ikke tilgjengelig: %s',
        'FSR 4 inte tillgänglig: %s', 'FSR 4 ei käytettävissä: %s', 'FSR 4 niedostępne: %s', 'FSR 4 nedostupné: %s',
        'Το FSR 4 δεν είναι διαθέσιμο: %s', 'FSR 4 недоступен: %s', 'FSR 4 kullanılamıyor: %s'),
    'The mode selected above is active. FSR 4 can be selected again.': R(
        'De modus die hierboven is gekozen is actief. FSR 4 kan opnieuw worden gekozen.',
        'Den tilstand, der er valgt ovenfor, er aktiv. FSR 4 kan vælges igen.',
        'Modusen som er valgt ovenfor, er aktiv. FSR 4 kan velges igjen.',
        'Läget som valts ovan är aktivt. FSR 4 kan väljas igen.',
        'Yllä valittu tila on käytössä. FSR 4 voidaan valita uudelleen.',
        'Tryb wybrany powyżej jest aktywny. FSR 4 można wybrać ponownie.',
        'Režim vybraný výše je aktivní. FSR 4 lze znovu vybrat.',
        'Η λειτουργία που επιλέχθηκε παραπάνω είναι ενεργή. Το FSR 4 μπορεί να επιλεγεί ξανά.',
        'Выбранный выше режим активен. FSR 4 можно выбрать снова.',
        'Yukarıda seçilen mod etkin. FSR 4 yeniden seçilebilir.'),
    'Smooths edges and keeps the picture stable from frame to frame; with an upscaled render resolution it also '
    'rebuilds the full size. DLSS needs a GeForce RTX card.': R(
        'Maakt randen glad en houdt het beeld stabiel van frame tot frame; met een opgeschaalde renderresolutie bouwt '
        'het ook het volle formaat op. DLSS vereist een GeForce RTX-kaart.',
        'Udglatter kanter og holder billedet stabilt fra billede til billede; med en opskaleret renderopløsning '
        'genskaber den også den fulde størrelse. DLSS kræver et GeForce RTX-kort.',
        'Glatter kanter og holder bildet stabilt fra bilde til bilde; med en oppskalert renderoppløsning gjenskaper '
        'den også full størrelse. DLSS krever et GeForce RTX-kort.',
        'Jämnar ut kanter och håller bilden stabil från bildruta till bildruta; med en uppskalad renderupplösning '
        'återskapar den även full storlek. DLSS kräver ett GeForce RTX-kort.',
        'Pehmentää reunat ja pitää kuvan vakaana kuvasta toiseen; skaalatulla renderöintitarkkuudella se myös '
        'rakentaa täyden koon. DLSS vaatii GeForce RTX -näytönohjaimen.',
        'Wygładza krawędzie i utrzymuje obraz stabilnym z klatki na klatkę; przy skalowanej rozdzielczości '
        'renderowania odtwarza też pełny rozmiar. DLSS wymaga karty GeForce RTX.',
        'Vyhlazuje hrany a drží obraz stabilní ze snímku na snímek; při škálovaném rozlišení vykreslování také '
        'obnoví plnou velikost. DLSS vyžaduje kartu GeForce RTX.',
        'Εξομαλύνει τα άκρα και κρατά την εικόνα σταθερή από καρέ σε καρέ· με κλιμακωμένη ανάλυση απόδοσης ανακτά '
        'επίσης το πλήρες μέγεθος. Το DLSS χρειάζεται κάρτα GeForce RTX.',
        'Сглаживает края и сохраняет картинку стабильной от кадра к кадру; при масштабируемом разрешении рендеринга '
        'также восстанавливает полный размер. Для DLSS нужна видеокарта GeForce RTX.',
        'Kenarları yumuşatır ve görüntüyü kareden kareye sabit tutar; yükseltilmiş işleme çözünürlüğünde tam boyutu '
        'da yeniden oluşturur. DLSS için GeForce RTX kart gerekir.'),
    'Sharpness': R('Scherpte', 'Skarphed', 'Skarphet', 'Skärpa', 'Terävyys', 'Ostrość', 'Ostrost', 'Ευκρίνεια',
                   'Резкость', 'Keskinlik'),
    "Sharpens the anti-aliased picture (AMD RCAS, also with DLSS). 0 is off; the launcher's Low, Medium and High are "
    "0.2, 0.4 and 0.7. Ctrl+click to type a value.": R(
        'Verscherpt het gladgemaakte beeld (AMD RCAS, ook met DLSS). 0 is uit; Laag, Gemiddeld en Hoog in de launcher '
        'zijn 0.2, 0.4 en 0.7. Ctrl+klik om een waarde te typen.',
        'Gør det kantudjævnede billede skarpere (AMD RCAS, også med DLSS). 0 er fra; launcherens Lav, Medium og Høj er '
        '0.2, 0.4 og 0.7. Ctrl+klik for at skrive en værdi.',
        'Gjør det kantutjevnede bildet skarpere (AMD RCAS, også med DLSS). 0 er av; launcherens Lav, Middels og Høy er '
        '0.2, 0.4 og 0.7. Ctrl+klikk for å skrive inn en verdi.',
        'Skärper den kantutjämnade bilden (AMD RCAS, även med DLSS). 0 är av; launcherns Låg, Medel och Hög är 0.2, '
        '0.4 och 0.7. Ctrl+klicka för att skriva ett värde.',
        'Terävöittää reunanpehmennetyn kuvan (AMD RCAS, myös DLSS:n kanssa). 0 on pois; käynnistimen Matala, '
        'Keskitaso ja Korkea ovat 0.2, 0.4 ja 0.7. Ctrl+napsautus kirjoittaa arvon.',
        'Wyostrza wygładzony obraz (AMD RCAS, także z DLSS). 0 to wyłączone; Niskie, Średnie i Wysokie w launcherze '
        'to 0.2, 0.4 i 0.7. Ctrl+klik, aby wpisać wartość.',
        'Doostří vyhlazený obraz (AMD RCAS, i s DLSS). 0 je vypnuto; Nízké, Střední a Vysoké v launcheru jsou 0.2, '
        '0.4 a 0.7. Ctrl+kliknutí pro zadání hodnoty.',
        'Οξύνει την εξομαλυμένη εικόνα (AMD RCAS, και με DLSS). Το 0 είναι ανενεργό· τα Χαμηλή, Μεσαία και Υψηλή του '
        'launcher είναι 0.2, 0.4 και 0.7. Ctrl+κλικ για να πληκτρολογήσετε τιμή.',
        'Повышает резкость сглаженной картинки (AMD RCAS, также с DLSS). 0 - выкл.; Низкие, Средние и Высокие в '
        'лаунчере - это 0.2, 0.4 и 0.7. Ctrl+щелчок, чтобы ввести значение.',
        "Kenarları yumuşatılmış görüntüyü keskinleştirir (AMD RCAS, DLSS ile de). 0 kapalıdır; başlatıcının Düşük, "
        "Orta ve Yüksek ayarları 0.2, 0.4 ve 0.7'dir. Değer yazmak için Ctrl+tıklayın."),
    'Frame generation': R(
        'Framegeneratie', 'Billedgenerering', 'Bildegenerering', 'Bildrutegenerering', 'Kuvien generointi',
        'Generowanie klatek', 'Generování snímků', 'Δημιουργία καρέ', 'Генерация кадров', 'Kare oluşturma'),
    'Off': R('Uit', 'Fra', 'Av', 'Av', 'Pois', 'Wył.', 'Vypnuto', 'Ανενεργό', 'Выкл.', 'Kapalı'),
    'FSR 3 (any graphics card)': R(
        'FSR 3 (elke videokaart)', 'FSR 3 (alle grafikkort)', 'FSR 3 (alle grafikkort)', 'FSR 3 (alla grafikkort)',
        'FSR 3 (mikä tahansa näytönohjain)', 'FSR 3 (każda karta graficzna)', 'FSR 3 (jakákoli grafická karta)',
        'FSR 3 (οποιαδήποτε κάρτα γραφικών)', 'FSR 3 (любая видеокарта)', 'FSR 3 (her ekran kartı)'),
    'Multiplier': R('Vermenigvuldiger', 'Multiplikator', 'Multiplikator', 'Multiplikator', 'Kerroin', 'Mnożnik',
                    'Násobič', 'Πολλαπλασιαστής', 'Множитель', 'Çarpan'),
    "Generated frames between the game's own: 60 FPS on screen becomes 120. Adds a little input latency; menus and "
    "cutscene videos are not generated. The launcher's Frame rate limit counts generated frames.": R(
        'Gegenereerde frames tussen die van de game: 60 FPS op het scherm wordt 120. Geeft iets meer invoervertraging; '
        'menu\'s en tussenfilmpjes worden niet gegenereerd. De Framerate-limiet van de launcher telt gegenereerde '
        'frames mee.',
        'Genererede billeder mellem spillets egne: 60 FPS på skærmen bliver til 120. Giver lidt mere inputforsinkelse; '
        'menuer og mellemsekvenser genereres ikke. Launcherens Grænse for billedhastighed tæller genererede billeder '
        'med.',
        'Genererte bilder mellom spillets egne: 60 FPS på skjermen blir 120. Gir litt mer inndataforsinkelse; menyer '
        'og mellomsekvenser genereres ikke. Launcherens Grense for bildefrekvens teller med genererte bilder.',
        'Genererade bildrutor mellan spelets egna: 60 FPS på skärmen blir 120. Ger lite mer indatafördröjning; menyer '
        'och mellansekvenser genereras inte. Launcherns Gräns för bildfrekvens räknar med genererade bildrutor.',
        'Generoituja kuvia pelin omien välissä: 60 FPS ruudulla muuttuu 120:ksi. Lisää hieman syöteviivettä; '
        'valikoita ja välivideoita ei generoida. Käynnistimen Kuvataajuuden rajoitus laskee generoidut kuvat mukaan.',
        'Generowane klatki między klatkami gry: 60 FPS na ekranie zmienia się w 120. Dodaje trochę opóźnienia '
        'sterowania; menu i filmiki nie są generowane. Limit klatek w launcherze liczy klatki generowane.',
        'Generované snímky mezi snímky hry: 60 FPS na obrazovce se změní na 120. Přidá trochu zpoždění vstupu; '
        'nabídky a videa v animacích se negenerují. Limit snímkové frekvence v launcheru počítá i generované snímky.',
        'Παραγόμενα καρέ ανάμεσα σε αυτά του παιχνιδιού: τα 60 FPS στην οθόνη γίνονται 120. Προσθέτει λίγη '
        'καθυστέρηση εισόδου· τα μενού και τα βίντεο σκηνών δεν παράγονται. Το Όριο ρυθμού καρέ του launcher μετρά '
        'και τα παραγόμενα καρέ.',
        'Сгенерированные кадры между кадрами игры: 60 FPS на экране становятся 120. Немного увеличивает задержку '
        'ввода; меню и видеоролики не генерируются. Ограничение частоты кадров в лаунчере учитывает сгенерированные '
        'кадры.',
        "Oyunun kendi kareleri arasına oluşturulan kareler: ekrandaki 60 FPS 120 olur. Girişe biraz gecikme ekler; "
        "menüler ve ara sahne videoları oluşturulmaz. Başlatıcının Kare hızı sınırı oluşturulan kareleri de sayar."),
    'Other': R('Overig', 'Andet', 'Annet', 'Övrigt', 'Muut', 'Inne', 'Ostatní', 'Άλλα', 'Прочее', 'Diğer'),
    'FPS counter in the corner': R(
        'FPS-teller in de hoek', 'FPS-tæller i hjørnet', 'FPS-teller i hjørnet', 'FPS-räknare i hörnet',
        'FPS-laskuri kulmassa', 'Licznik FPS w rogu', 'Počítadlo FPS v rohu', 'Μετρητής FPS στη γωνία',
        'Счётчик FPS в углу', 'Köşede FPS sayacı'),
    'Frame time graph': R(
        'Frametijdgrafiek', 'Billedtidsgraf', 'Bildetidsgraf', 'Bildrutetidsgraf', 'Kuva-aikakaavio',
        'Wykres czasu klatki', 'Graf doby snímku', 'Γράφημα χρόνου καρέ', 'График времени кадра', 'Kare süresi grafiği'),
    "Top line, the game's own frames: FPS and frame time, 1%L the average of the slowest 1% (stutter), MAX the slowest "
    "frame (last 5 seconds). Below: the anti-aliasing, the render size (Q, B, P: Quality, Balanced, Performance) and "
    "with frame generation FG, the frames on screen. The graph: the game's frame times, a spike is a hitch.": R(
        'Bovenste regel, de eigen frames van de game: FPS en frametijd, 1%L het gemiddelde van de traagste 1% '
        '(haperingen), MAX het traagste frame (laatste 5 seconden). Daaronder: de anti-aliasing, de rendergrootte '
        '(Q, B, P: Kwaliteit, Gebalanceerd, Prestaties) en met framegeneratie FG, de frames op het scherm. De '
        'grafiek: de frametijden van de game, een piek is een hapering.',
        'Øverste linje, spillets egne billeder: FPS og billedtid, 1%L gennemsnittet af de langsomste 1% (hakken), MAX '
        'det langsomste billede (seneste 5 sekunder). Nedenunder: kantudjævningen, renderstørrelsen (Q, B, P: '
        'Kvalitet, Balanceret, Ydeevne) og med billedgenerering FG, billederne på skærmen. Grafen: spillets '
        'billedtider, en top er et hak.',
        'Øverste linje, spillets egne bilder: FPS og bildetid, 1%L snittet av de tregeste 1% (hakking), MAX det '
        'tregeste bildet (siste 5 sekunder). Under: kantutjevningen, renderstørrelsen (Q, B, P: Kvalitet, Balansert, '
        'Ytelse) og med bildegenerering FG, bildene på skjermen. Grafen: spillets bildetider, en topp er et hakk.',
        'Översta raden, spelets egna bildrutor: FPS och bildrutetid, 1%L snittet av de långsammaste 1% (hack), MAX '
        'den långsammaste bildrutan (senaste 5 sekunderna). Nedanför: kantutjämningen, renderstorleken (Q, B, P: '
        'Kvalitet, Balanserad, Prestanda) och med bildrutegenerering FG, bildrutorna på skärmen. Grafen: spelets '
        'bildrutetider, en topp är ett hack.',
        'Ylin rivi, pelin omat kuvat: FPS ja kuva-aika, 1%L hitaimman 1%:n keskiarvo (nykiminen), MAX hitain kuva '
        '(viimeiset 5 sekuntia). Alla: reunanpehmennys, renderöintikoko (Q, B, P: Laatu, Tasapainoinen, '
        'Suorituskyky) ja kuvien generoinnin kanssa FG, kuvat ruudulla. Kaavio: pelin kuva-ajat, piikki on nykäys.',
        'Górna linia, własne klatki gry: FPS i czas klatki, 1%L średnia najwolniejszego 1% (przycięcia), MAX '
        'najwolniejsza klatka (ostatnie 5 sekund). Niżej: wygładzanie krawędzi, rozmiar renderowania (Q, B, P: '
        'Jakość, Zrównoważona, Wydajność) i przy generowaniu klatek FG, klatki na ekranie. Wykres: czasy klatek gry, '
        'skok to przycięcie.',
        'Horní řádek, vlastní snímky hry: FPS a doba snímku, 1%L průměr nejpomalejšího 1 % (zadrhávání), MAX '
        'nejpomalejší snímek (posledních 5 sekund). Pod ním: vyhlazování hran, velikost vykreslování (Q, B, P: '
        'Kvalita, Vyvážený, Výkon) a s generováním snímků FG, snímky na obrazovce. Graf: doby snímků hry, špička je '
        'zadrhnutí.',
        'Πάνω γραμμή, τα καρέ του ίδιου του παιχνιδιού: FPS και χρόνος καρέ, 1%L ο μέσος όρος του πιο αργού 1% '
        '(κολλήματα), MAX το πιο αργό καρέ (τελευταία 5 δευτερόλεπτα). Από κάτω: η εξομάλυνση άκρων, το μέγεθος '
        'απόδοσης (Q, B, P: Ποιότητα, Ισορροπημένο, Επιδόσεις) και με δημιουργία καρέ FG, τα καρέ στην οθόνη. Το '
        'γράφημα: οι χρόνοι καρέ του παιχνιδιού, μια κορυφή είναι κόλλημα.',
        'Верхняя строка, собственные кадры игры: FPS и время кадра, 1%L среднее самых медленных 1% (рывки), MAX самый '
        'медленный кадр (последние 5 секунд). Ниже: сглаживание, размер рендеринга (Q, B, P: Качество, Баланс, '
        'Производительность) и при генерации кадров FG, кадры на экране. График: время кадров игры, пик - это рывок.',
        'Üst satır, oyunun kendi kareleri: FPS ve kare süresi, 1%L en yavaş %1\'in ortalaması (takılma), MAX en yavaş '
        'kare (son 5 saniye). Altında: kenar yumuşatma, işleme boyutu (Q, B, P: Kalite, Dengeli, Performans) ve kare '
        'oluşturmayla FG, ekrandaki kareler. Grafik: oyunun kare süreleri, bir sivrilme bir takılmadır.'),
    'Developer options': R(
        'Ontwikkelaarsopties', 'Udviklerindstillinger', 'Utvikleralternativer', 'Utvecklaralternativ',
        'Kehittäjäasetukset', 'Opcje deweloperskie', 'Možnosti pro vývojáře', 'Επιλογές προγραμματιστή',
        'Параметры разработчика', 'Geliştirici seçenekleri'),
    'Sub-pixel jitter': R(
        'Subpixel-jitter', 'Subpixel-jitter', 'Subpiksel-jitter', 'Subpixel-jitter', 'Alipikselivärinä',
        'Drgania subpikselowe', 'Subpixelový jitter', 'Jitter υποεικονοστοιχείου', 'Субпиксельный джиттер',
        'Alt piksel titreşimi'),
    'Each frame the scene shifts by a fraction of a pixel and the anti-aliasing gathers detail from several frames. '
    'Off: smoothing from the history only.': R(
        'Elk frame verschuift de scène een fractie van een pixel en de anti-aliasing verzamelt detail uit meerdere '
        'frames. Uit: alleen gladmaken uit de geschiedenis.',
        'Hvert billede flyttes scenen en brøkdel af en pixel, og kantudjævningen samler detaljer fra flere billeder. '
        'Fra: kun udglatning fra historikken.',
        'Hvert bilde flyttes scenen en brøkdel av en piksel, og kantutjevningen samler detaljer fra flere bilder. Av: '
        'bare utjevning fra historikken.',
        'Varje bildruta flyttas scenen en bråkdel av en pixel och kantutjämningen samlar detaljer från flera '
        'bildrutor. Av: utjämning bara från historiken.',
        'Joka kuvassa näkymä siirtyy pikselin murto-osan, ja reunanpehmennys kerää yksityiskohtia useista kuvista. '
        'Pois: pehmennys vain historiasta.',
        'W każdej klatce scena przesuwa się o ułamek piksela, a wygładzanie zbiera szczegóły z kilku klatek. Wył.: '
        'wygładzanie tylko z historii.',
        'Každý snímek se scéna posune o zlomek pixelu a vyhlazování sbírá detaily z několika snímků. Vypnuto: '
        'vyhlazování jen z historie.',
        'Σε κάθε καρέ η σκηνή μετατοπίζεται κατά ένα κλάσμα του pixel και η εξομάλυνση συλλέγει λεπτομέρεια από '
        'πολλά καρέ. Ανενεργό: εξομάλυνση μόνο από το ιστορικό.',
        'В каждом кадре сцена сдвигается на долю пикселя, и сглаживание собирает детали из нескольких кадров. Выкл.: '
        'сглаживание только по истории.',
        'Her karede sahne bir pikselin kesri kadar kayar ve kenar yumuşatma ayrıntıyı birkaç kareden toplar. Kapalı: '
        'yalnızca geçmişten yumuşatma.'),
    'Sharpening pass': R(
        'Verscherpingsstap', 'Skarphedspas', 'Skarphetspass', 'Skärpningspass', 'Terävöintivaihe',
        'Przebieg wyostrzania', 'Průchod doostření', 'Πέρασμα όξυνσης', 'Проход резкости', 'Keskinleştirme geçişi'),
    'FSR 4: auto exposure': R(
        'FSR 4: automatische belichting', 'FSR 4: automatisk eksponering', 'FSR 4: automatisk eksponering',
        'FSR 4: automatisk exponering', 'FSR 4: automaattinen valotus', 'FSR 4: automatyczna ekspozycja',
        'FSR 4: automatická expozice', 'FSR 4: αυτόματη έκθεση', 'FSR 4: автоэкспозиция', 'FSR 4: otomatik pozlama'),
    'FSR 4: inverted jitter sign': R(
        'FSR 4: omgekeerd jitterteken', 'FSR 4: omvendt jitter-fortegn', 'FSR 4: omvendt jitter-fortegn',
        'FSR 4: omvänt jitter-tecken', 'FSR 4: käänteinen värinän etumerkki', 'FSR 4: odwrócony znak drgań',
        'FSR 4: obrácené znaménko jitteru', 'FSR 4: αντεστραμμένο πρόσημο jitter', 'FSR 4: инвертированный знак джиттера',
        'FSR 4: ters titreşim işareti'),
    'Reactive mask': R(
        'Reactief masker', 'Reaktiv maske', 'Reaktiv maske', 'Reaktiv mask', 'Reaktiivinen maski', 'Maska reaktywna',
        'Reaktivní maska', 'Αντιδραστική μάσκα', 'Реактивная маска', 'Reaktif maske'),
    'Marks transparent effects (particles, haze) so the upscaler relies less on past frames: fewer trails behind '
    'effects, more shimmer under them.': R(
        'Markeert transparante effecten (deeltjes, nevel) zodat de upscaler minder op vorige frames leunt: minder '
        'sporen achter effecten, meer flikkering eronder.',
        'Markerer gennemsigtige effekter (partikler, dis), så opskaleringen læner sig mindre på tidligere billeder: '
        'færre spor bag effekter, mere flimmer under dem.',
        'Markerer gjennomsiktige effekter (partikler, dis) slik at oppskaleringen lener seg mindre på tidligere '
        'bilder: færre spor bak effekter, mer flimring under dem.',
        'Markerar genomskinliga effekter (partiklar, dis) så att uppskalningen förlitar sig mindre på tidigare '
        'bildrutor: färre spår bakom effekter, mer flimmer under dem.',
        'Merkitsee läpinäkyvät tehosteet (hiukkaset, usva), jotta skaalain nojaa vähemmän aiempiin kuviin: vähemmän '
        'jälkiä tehosteiden takana, enemmän välkettä niiden alla.',
        'Oznacza przezroczyste efekty (cząsteczki, mgiełka), aby skalowanie mniej polegało na poprzednich klatkach: '
        'mniej smug za efektami, więcej migotania pod nimi.',
        'Označí průhledné efekty (částice, opar), aby se škálování méně spoléhalo na minulé snímky: méně stop za '
        'efekty, více mihotání pod nimi.',
        'Σημαδεύει τα διαφανή εφέ (σωματίδια, αχλή) ώστε η κλιμάκωση να βασίζεται λιγότερο σε προηγούμενα καρέ: '
        'λιγότερα ίχνη πίσω από εφέ, περισσότερο τρεμόπαιγμα κάτω από αυτά.',
        'Отмечает прозрачные эффекты (частицы, дымка), чтобы апскейлер меньше опирался на прошлые кадры: меньше '
        'шлейфов за эффектами, больше мерцания под ними.',
        'Saydam efektleri (parçacıklar, pus) işaretler, böylece yükseltici geçmiş karelere daha az dayanır: '
        'efektlerin arkasında daha az iz, altlarında daha fazla parıltı.'),
    'Mask scale': R(
        'Maskerschaal', 'Maskeskala', 'Maskeskala', 'Maskskala', 'Maskin skaala', 'Skala maski', 'Měřítko masky',
        'Κλίμακα μάσκας', 'Масштаб маски', 'Maske ölçeği'),
    'Mask threshold': R(
        'Maskerdrempel', 'Maskegrænse', 'Masketerskel', 'Masktröskel', 'Maskin kynnys', 'Próg maski', 'Práh masky',
        'Κατώφλι μάσκας', 'Порог маски', 'Maske eşiği'),
    'Mask maximum': R(
        'Maskermaximum', 'Maskemaksimum', 'Maskemaksimum', 'Maskmaximum', 'Maskin maksimi', 'Maksimum maski',
        'Maximum masky', 'Μέγιστο μάσκας', 'Максимум маски', 'Maske üst sınırı'),
    'Show the mask': R(
        'Masker tonen', 'Vis masken', 'Vis masken', 'Visa masken', 'Näytä maski', 'Pokaż maskę', 'Zobrazit masku',
        'Εμφάνιση μάσκας', 'Показать маску', 'Maskeyi göster'),
    'Character motion vectors': R(
        'Bewegingsvectoren van personages', 'Bevægelsesvektorer for figurer', 'Bevegelsesvektorer for figurer',
        'Rörelsevektorer för figurer', 'Hahmojen liikevektorit', 'Wektory ruchu postaci', 'Vektory pohybu postav',
        'Διανύσματα κίνησης χαρακτήρων', 'Векторы движения персонажей', 'Karakter hareket vektörleri'),
    'Exact vectors for animated objects (applies after restarting the game).': R(
        'Exacte vectoren voor geanimeerde objecten (geldt na een herstart van de game).',
        'Præcise vektorer for animerede objekter (gælder efter genstart af spillet).',
        'Nøyaktige vektorer for animerte objekter (gjelder etter omstart av spillet).',
        'Exakta vektorer för animerade objekt (gäller efter omstart av spelet).',
        'Tarkat vektorit animoiduille kohteille (tulee voimaan pelin uudelleenkäynnistyksen jälkeen).',
        'Dokładne wektory dla animowanych obiektów (działa po ponownym uruchomieniu gry).',
        'Přesné vektory pro animované objekty (platí po restartu hry).',
        'Ακριβή διανύσματα για κινούμενα αντικείμενα (ισχύει μετά την επανεκκίνηση του παιχνιδιού).',
        'Точные векторы для анимированных объектов (применяется после перезапуска игры).',
        'Hareketli nesneler için tam vektörler (oyun yeniden başlatıldıktan sonra uygulanır).'),
    'Show the motion vectors': R(
        'Bewegingsvectoren tonen', 'Vis bevægelsesvektorerne', 'Vis bevegelsesvektorene', 'Visa rörelsevektorerna',
        'Näytä liikevektorit', 'Pokaż wektory ruchu', 'Zobrazit vektory pohybu', 'Εμφάνιση διανυσμάτων κίνησης',
        'Показать векторы движения', 'Hareket vektörlerini göster'),
    'Red/green: horizontal/vertical motion (8 pixels = full brightness); blue: an exact object vector.': R(
        'Rood/groen: horizontale/verticale beweging (8 pixels = volle helderheid); blauw: een exacte objectvector.',
        'Rød/grøn: vandret/lodret bevægelse (8 pixels = fuld lysstyrke); blå: en præcis objektvektor.',
        'Rød/grønn: vannrett/loddrett bevegelse (8 piksler = full lysstyrke); blå: en nøyaktig objektvektor.',
        'Röd/grön: vågrät/lodrät rörelse (8 pixlar = full ljusstyrka); blå: en exakt objektvektor.',
        'Punainen/vihreä: vaaka-/pystyliike (8 pikseliä = täysi kirkkaus); sininen: tarkka kohteen vektori.',
        'Czerwony/zielony: ruch poziomy/pionowy (8 pikseli = pełna jasność); niebieski: dokładny wektor obiektu.',
        'Červená/zelená: vodorovný/svislý pohyb (8 pixelů = plný jas); modrá: přesný vektor objektu.',
        'Κόκκινο/πράσινο: οριζόντια/κάθετη κίνηση (8 pixel = πλήρης φωτεινότητα)· μπλε: ακριβές διάνυσμα αντικειμένου.',
        'Красный/зелёный: движение по горизонтали/вертикали (8 пикселей = полная яркость); синий: точный вектор '
        'объекта.',
        'Kırmızı/yeşil: yatay/dikey hareket (8 piksel = tam parlaklık); mavi: tam bir nesne vektörü.'),
    'Changes apply after restarting the game': R(
        'Wijzigingen gelden na een herstart van de game', 'Ændringer gælder efter genstart af spillet',
        'Endringer gjelder etter omstart av spillet', 'Ändringar gäller efter omstart av spelet',
        'Muutokset tulevat voimaan pelin uudelleenkäynnistyksen jälkeen',
        'Zmiany działają po ponownym uruchomieniu gry', 'Změny platí po restartu hry',
        'Οι αλλαγές ισχύουν μετά την επανεκκίνηση του παιχνιδιού', 'Изменения применятся после перезапуска игры',
        'Değişiklikler oyun yeniden başlatıldıktan sonra uygulanır'),
    'Apply and restart the game': R(
        'Toepassen en de game herstarten', 'Anvend og genstart spillet', 'Bruk og start spillet på nytt',
        'Verkställ och starta om spelet', 'Ota käyttöön ja käynnistä peli uudelleen',
        'Zastosuj i uruchom grę ponownie', 'Použít a restartovat hru', 'Εφαρμογή και επανεκκίνηση του παιχνιδιού',
        'Применить и перезапустить игру', 'Uygula ve oyunu yeniden başlat'),
    'Checkpoints': R(
        'Checkpoints', 'Checkpoints', 'Sjekkpunkter', 'Kontrollpunkter', 'Tarkistuspisteet', 'Punkty kontrolne',
        'Kontrolní body', 'Σημεία ελέγχου', 'Контрольные точки', 'Kontrol noktaları'),
    'Save slots': R(
        'Opslagslots', 'Gemmepladser', 'Lagringsplasser', 'Sparplatser', 'Tallennuspaikat', 'Sloty zapisu',
        'Sloty pozic', 'Θέσεις αποθήκευσης', 'Слоты сохранений', 'Kayıt yuvaları'),
    'Close': R('Sluiten', 'Luk', 'Lukk', 'Stäng', 'Sulje', 'Zamknij', 'Zavřít', 'Κλείσιμο', 'Закрыть', 'Kapat'),

    # ---- Over the game: trophies, screenshots ----------------------------------------------------------------------
    'Platinum trophy earned': R(
        'Platina trofee behaald', 'Platintrofæ optjent', 'Platinatrofé oppnådd', 'Platinatrofé erhållen',
        'Platinapalkinto ansaittu', 'Zdobyto platynowe trofeum', 'Získána platinová trofej',
        'Κερδίσατε πλατινένιο τρόπαιο', 'Получен платиновый трофей', 'Platin kupa kazanıldı'),
    'Gold trophy earned': R(
        'Gouden trofee behaald', 'Guldtrofæ optjent', 'Gulltrofé oppnådd', 'Guldtrofé erhållen',
        'Kultapalkinto ansaittu', 'Zdobyto złote trofeum', 'Získána zlatá trofej', 'Κερδίσατε χρυσό τρόπαιο',
        'Получен золотой трофей', 'Altın kupa kazanıldı'),
    'Silver trophy earned': R(
        'Zilveren trofee behaald', 'Sølvtrofæ optjent', 'Sølvtrofé oppnådd', 'Silvertrofé erhållen',
        'Hopeapalkinto ansaittu', 'Zdobyto srebrne trofeum', 'Získána stříbrná trofej', 'Κερδίσατε ασημένιο τρόπαιο',
        'Получен серебряный трофей', 'Gümüş kupa kazanıldı'),
    'Bronze trophy earned': R(
        'Bronzen trofee behaald', 'Bronzetrofæ optjent', 'Bronsetrofé oppnådd', 'Bronstrofé erhållen',
        'Pronssipalkinto ansaittu', 'Zdobyto brązowe trofeum', 'Získána bronzová trofej', 'Κερδίσατε χάλκινο τρόπαιο',
        'Получен бронзовый трофей', 'Bronz kupa kazanıldı'),
    'Screenshot saved': R(
        'Screenshot opgeslagen', 'Skærmbillede gemt', 'Skjermbilde lagret', 'Skärmbild sparad',
        'Kuvakaappaus tallennettu', 'Zrzut ekranu zapisany', 'Snímek obrazovky uložen',
        'Το στιγμιότυπο αποθηκεύτηκε', 'Снимок сохранён', 'Ekran görüntüsü kaydedildi'),

    # ---- Shader preparation page ------------------------------------------------------------------------------------
    'about {:.0f} min left': R(
        'nog ongeveer {:.0f} min', 'ca. {:.0f} min tilbage', 'ca. {:.0f} min igjen', 'ca. {:.0f} min kvar',
        'noin {:.0f} min jäljellä', 'zostało ok. {:.0f} min', 'zbývá asi {:.0f} min',
        'απομένουν περίπου {:.0f} λεπτά', 'осталось около {:.0f} мин', 'yaklaşık {:.0f} dk kaldı'),
    'about {:.0f} s left': R(
        'nog ongeveer {:.0f} s', 'ca. {:.0f} s tilbage', 'ca. {:.0f} s igjen', 'ca. {:.0f} s kvar',
        'noin {:.0f} s jäljellä', 'zostało ok. {:.0f} s', 'zbývá asi {:.0f} s', 'απομένουν περίπου {:.0f} δευτ.',
        'осталось около {:.0f} с', 'yaklaşık {:.0f} sn kaldı'),
    'Step 1 of 2: finding the shaders in your game files (only this once)': R(
        'Stap 1 van 2: de shaders in je gamebestanden zoeken (alleen deze ene keer)',
        'Trin 1 af 2: finder shaderne i dine spilfiler (kun denne ene gang)',
        'Trinn 1 av 2: finner shaderne i spillfilene dine (bare denne ene gangen)',
        'Steg 1 av 2: hittar shaders i dina spelfiler (bara den här gången)',
        'Vaihe 1/2: etsitään varjostimia pelitiedostoistasi (vain tämän kerran)',
        'Krok 1 z 2: szukanie shaderów w plikach gry (tylko ten jeden raz)',
        'Krok 1 ze 2: hledání shaderů v souborech hry (jen tentokrát)',
        'Βήμα 1 από 2: εύρεση των shader στα αρχεία του παιχνιδιού σας (μόνο αυτή τη φορά)',
        'Шаг 1 из 2: поиск шейдеров в файлах игры (только в этот раз)',
        'Adım 1/2: oyun dosyalarınızdaki gölgelendiriciler bulunuyor (yalnızca bu seferlik)'),
    'a few seconds left': R(
        'nog een paar seconden', 'få sekunder tilbage', 'noen sekunder igjen', 'några sekunder kvar',
        'muutama sekunti jäljellä', 'zostało kilka sekund', 'zbývá pár sekund', 'απομένουν λίγα δευτερόλεπτα',
        'осталось несколько секунд', 'birkaç saniye kaldı'),
    'about {} min {} s left': R(
        'nog ongeveer {} min {} s', 'ca. {} min {} s tilbage', 'ca. {} min {} s igjen', 'ca. {} min {} s kvar',
        'noin {} min {} s jäljellä', 'zostało ok. {} min {} s', 'zbývá asi {} min {} s',
        'απομένουν περίπου {} λεπτά {} δευτ.', 'осталось около {} мин {} с', 'yaklaşık {} dk {} sn kaldı'),
    'about {} s left': R(
        'nog ongeveer {} s', 'ca. {} s tilbage', 'ca. {} s igjen', 'ca. {} s kvar', 'noin {} s jäljellä',
        'zostało ok. {} s', 'zbývá asi {} s', 'απομένουν περίπου {} δευτ.', 'осталось около {} с',
        'yaklaşık {} sn kaldı'),
    'Preparing shaders': R(
        'Shaders voorbereiden', 'Forbereder shaders', 'Klargjør shadere', 'Förbereder shaders',
        'Valmistellaan varjostimia', 'Przygotowywanie shaderów', 'Příprava shaderů', 'Προετοιμασία shader',
        'Подготовка шейдеров', 'Gölgelendiriciler hazırlanıyor'),
    'Your graphics driver is compiling the shaders again (after a driver update or when its cache was cleared). The '
    'game continues when this is done.': R(
        'Je videodriver compileert de shaders opnieuw (na een driverupdate of als de cache is gewist). De game gaat '
        'verder als dit klaar is.',
        'Din grafikdriver kompilerer shaderne igen (efter en driveropdatering eller når dens cache er ryddet). '
        'Spillet fortsætter, når det er færdigt.',
        'Grafikkdriveren din kompilerer shaderne på nytt (etter en driveroppdatering eller når hurtigbufferen er '
        'tømt). Spillet fortsetter når dette er ferdig.',
        'Din grafikdrivrutin kompilerar shaders igen (efter en drivrutinsuppdatering eller när dess cache rensats). '
        'Spelet fortsätter när det är klart.',
        'Näytönohjaimesi ajuri kääntää varjostimet uudelleen (ajuripäivityksen jälkeen tai kun sen välimuisti on '
        'tyhjennetty). Peli jatkuu, kun tämä on valmis.',
        'Sterownik graficzny ponownie kompiluje shadery (po aktualizacji sterownika lub wyczyszczeniu jego pamięci). '
        'Gra będzie kontynuowana, gdy to się skończy.',
        'Grafický ovladač znovu kompiluje shadery (po aktualizaci ovladače nebo po vymazání jeho mezipaměti). Hra '
        'bude pokračovat, až to skončí.',
        'Το πρόγραμμα οδήγησης γραφικών σας μεταγλωττίζει ξανά τα shader (μετά από ενημέρωση οδηγού ή όταν '
        'εκκαθαρίστηκε η cache του). Το παιχνίδι συνεχίζει όταν τελειώσει.',
        'Графический драйвер заново компилирует шейдеры (после обновления драйвера или очистки его кэша). Игра '
        'продолжится, когда это закончится.',
        'Grafik sürücünüz gölgelendiricileri yeniden derliyor (sürücü güncellemesinden sonra veya önbelleği '
        'temizlendiğinde). Bu bitince oyun devam eder.'),
    'This happens once, before your first launch. Later launches start straight away.': R(
        'Dit gebeurt één keer, voor je eerste start. Latere starts beginnen meteen.',
        'Det sker én gang, før din første start. Senere starter går i gang med det samme.',
        'Dette skjer én gang, før den første oppstarten. Senere oppstarter går i gang med en gang.',
        'Detta sker en gång, före din första start. Senare starter kommer i gång direkt.',
        'Tämä tapahtuu kerran, ennen ensimmäistä käynnistystä. Myöhemmät käynnistykset alkavat heti.',
        'Dzieje się to raz, przed pierwszym uruchomieniem. Kolejne uruchomienia startują od razu.',
        'Děje se to jednou, před prvním spuštěním. Další spuštění začnou hned.',
        'Αυτό γίνεται μία φορά, πριν από την πρώτη εκκίνηση. Οι επόμενες εκκινήσεις ξεκινούν αμέσως.',
        'Это происходит один раз, перед первым запуском. Следующие запуски начинаются сразу.',
        'Bu, ilk başlatmadan önce bir kez olur. Sonraki başlatmalar hemen başlar.'),
    'Step 1 of 2: loading shaders': R(
        'Stap 1 van 2: shaders laden', 'Trin 1 af 2: indlæser shaders', 'Trinn 1 av 2: laster inn shadere',
        'Steg 1 av 2: läser in shaders', 'Vaihe 1/2: ladataan varjostimia', 'Krok 1 z 2: wczytywanie shaderów',
        'Krok 1 ze 2: načítání shaderů', 'Βήμα 1 από 2: φόρτωση shader', 'Шаг 1 из 2: загрузка шейдеров',
        'Adım 1/2: gölgelendiriciler yükleniyor'),
    'Step 1 of 2: building shaders from your game files': R(
        'Stap 1 van 2: shaders bouwen uit je gamebestanden', 'Trin 1 af 2: bygger shaders ud fra dine spilfiler',
        'Trinn 1 av 2: bygger shadere fra spillfilene dine', 'Steg 1 av 2: bygger shaders från dina spelfiler',
        'Vaihe 1/2: rakennetaan varjostimia pelitiedostoistasi', 'Krok 1 z 2: budowanie shaderów z plików gry',
        'Krok 1 ze 2: sestavení shaderů ze souborů hry', 'Βήμα 1 από 2: δημιουργία shader από τα αρχεία του παιχνιδιού',
        'Шаг 1 из 2: сборка шейдеров из файлов игры', 'Adım 1/2: gölgelendiriciler oyun dosyalarından oluşturuluyor'),
    'Step 2 of 2: compiling them for your graphics card': R(
        'Stap 2 van 2: ze compileren voor je videokaart', 'Trin 2 af 2: kompilerer dem til dit grafikkort',
        'Trinn 2 av 2: kompilerer dem for grafikkortet ditt', 'Steg 2 av 2: kompilerar dem för ditt grafikkort',
        'Vaihe 2/2: käännetään ne näytönohjaimellesi', 'Krok 2 z 2: kompilowanie ich dla twojej karty graficznej',
        'Krok 2 ze 2: kompilace pro vaši grafickou kartu', 'Βήμα 2 από 2: μεταγλώττιση για την κάρτα γραφικών σας',
        'Шаг 2 из 2: компиляция для вашей видеокарты', 'Adım 2/2: ekran kartınız için derleniyor'),
    'Finishing...': R(
        'Afronden...', 'Afslutter...', 'Fullfører...', 'Slutför...', 'Viimeistellään...', 'Kończenie...',
        'Dokončování...', 'Ολοκλήρωση...', 'Завершение...', 'Tamamlanıyor...'),
    'Starting...': R(
        'Starten...', 'Starter...', 'Starter...', 'Startar...', 'Käynnistetään...', 'Uruchamianie...',
        'Spouštění...', 'Εκκίνηση...', 'Запуск...', 'Başlatılıyor...'),
    'Finding the shaders in your game files (only this once) %.1f / %.1f GB%s': R(
        'Shaders zoeken in je gamebestanden (alleen deze ene keer) %.1f / %.1f GB%s',
        'Finder shaderne i dine spilfiler (kun denne ene gang) %.1f / %.1f GB%s',
        'Finner shaderne i spillfilene dine (bare denne ene gangen) %.1f / %.1f GB%s',
        'Hittar shaders i dina spelfiler (bara den här gången) %.1f / %.1f GB%s',
        'Etsitään varjostimia pelitiedostoistasi (vain tämän kerran) %.1f / %.1f GB%s',
        'Szukanie shaderów w plikach gry (tylko ten jeden raz) %.1f / %.1f GB%s',
        'Hledání shaderů v souborech hry (jen tentokrát) %.1f / %.1f GB%s',
        'Εύρεση των shader στα αρχεία του παιχνιδιού σας (μόνο αυτή τη φορά) %.1f / %.1f GB%s',
        'Поиск шейдеров в файлах игры (только в этот раз) %.1f / %.1f GB%s',
        'Oyun dosyalarınızda gölgelendiriciler aranıyor (yalnızca bu seferlik) %.1f / %.1f GB%s'),
    'Preparing pipelines': R(
        'Pipelines voorbereiden', 'Forbereder pipelines', 'Klargjør pipelines', 'Förbereder pipelines',
        'Valmistellaan pipelineja', 'Przygotowywanie potoków', 'Příprava pipeline', 'Προετοιμασία pipeline',
        'Подготовка конвейеров', "Pipeline'lar hazırlanıyor"),
    'Preparing shaders %u / %u%s': R(
        'Shaders voorbereiden %u / %u%s', 'Forbereder shaders %u / %u%s', 'Klargjør shadere %u / %u%s',
        'Förbereder shaders %u / %u%s', 'Valmistellaan varjostimia %u / %u%s', 'Przygotowywanie shaderów %u / %u%s',
        'Příprava shaderů %u / %u%s', 'Προετοιμασία shader %u / %u%s', 'Подготовка шейдеров %u / %u%s',
        'Gölgelendiriciler hazırlanıyor %u / %u%s'),
    'Preparing pipelines %u / %u%s': R(
        'Pipelines voorbereiden %u / %u%s', 'Forbereder pipelines %u / %u%s', 'Klargjør pipelines %u / %u%s',
        'Förbereder pipelines %u / %u%s', 'Valmistellaan pipelineja %u / %u%s', 'Przygotowywanie potoków %u / %u%s',
        'Příprava pipeline %u / %u%s', 'Προετοιμασία pipeline %u / %u%s', 'Подготовка конвейеров %u / %u%s',
        "Pipeline'lar hazırlanıyor %u / %u%s"),

    # ---- Save slots and checkpoint messages (bbport_saves.cpp) ------------------------------------------------------
    'Save slots are only for Uncharted 1, 2 and 3.': R(
        'Opslagslots zijn alleen voor Uncharted 1, 2 en 3.', 'Gemmepladser findes kun til Uncharted 1, 2 og 3.',
        'Lagringsplasser finnes bare for Uncharted 1, 2 og 3.', 'Sparplatser finns bara för Uncharted 1, 2 och 3.',
        'Tallennuspaikat ovat vain Uncharted 1, 2 ja 3 -peleille.', 'Sloty zapisu są tylko dla Uncharted 1, 2 i 3.',
        'Sloty pozic jsou jen pro Uncharted 1, 2 a 3.', 'Οι θέσεις αποθήκευσης είναι μόνο για τα Uncharted 1, 2 και 3.',
        'Слоты сохранений есть только для Uncharted 1, 2 и 3.', 'Kayıt yuvaları yalnızca Uncharted 1, 2 ve 3 içindir.'),
    'The game is saving: try again in a moment.': R(
        'De game is aan het opslaan: probeer het zo opnieuw.', 'Spillet gemmer: prøv igen om et øjeblik.',
        'Spillet lagrer: prøv igjen om et øyeblikk.', 'Spelet sparar: försök igen om en stund.',
        'Peli tallentaa: yritä hetken päästä uudelleen.', 'Gra zapisuje: spróbuj ponownie za chwilę.',
        'Hra ukládá: zkuste to za chvíli znovu.', 'Το παιχνίδι αποθηκεύει: δοκιμάστε ξανά σε λίγο.',
        'Игра сохраняется: попробуйте ещё раз через мгновение.', 'Oyun kaydediyor: birazdan tekrar deneyin.'),
    'Nothing to save yet: the game has not saved since the jump.': R(
        'Nog niets om op te slaan: de game heeft sinds de sprong niet opgeslagen.',
        'Intet at gemme endnu: spillet har ikke gemt siden springet.',
        'Ingenting å lagre ennå: spillet har ikke lagret siden hoppet.',
        'Inget att spara än: spelet har inte sparat sedan hoppet.',
        'Ei vielä mitään tallennettavaa: peli ei ole tallentanut hypyn jälkeen.',
        'Nie ma jeszcze czego zapisać: gra nie zapisywała od skoku.',
        'Zatím není co uložit: hra od skoku neukládala.',
        'Τίποτα για αποθήκευση ακόμη: το παιχνίδι δεν έχει αποθηκεύσει από το άλμα.',
        'Пока нечего сохранять: игра не сохранялась после перехода.',
        'Henüz kaydedilecek bir şey yok: oyun atlamadan beri kaydetmedi.'),
    'There is no campaign save yet.': R(
        'Er is nog geen campagne-opslag.', 'Der er ingen kampagnegemning endnu.', 'Det finnes ingen kampanjelagring ennå.',
        'Det finns ingen kampanjsparfil än.', 'Kampanjatallennusta ei ole vielä.', 'Nie ma jeszcze zapisu kampanii.',
        'Zatím neexistuje pozice kampaně.', 'Δεν υπάρχει ακόμη αποθήκευση εκστρατείας.', 'Сохранения кампании пока нет.',
        'Henüz hikâye kaydı yok.'),
    'Could not copy the save: {}': R(
        'Kon de opslag niet kopiëren: {}', 'Kunne ikke kopiere gemningen: {}', 'Kunne ikke kopiere lagringen: {}',
        'Kunde inte kopiera sparfilen: {}', 'Tallennusta ei voitu kopioida: {}', 'Nie udało się skopiować zapisu: {}',
        'Pozici se nepodařilo zkopírovat: {}', 'Δεν ήταν δυνατή η αντιγραφή της αποθήκευσης: {}',
        'Не удалось скопировать сохранение: {}', 'Kayıt kopyalanamadı: {}'),
    'Saved in slot {}.': R(
        'Opgeslagen in slot {}.', 'Gemt på plads {}.', 'Lagret på plass {}.', 'Sparat på plats {}.',
        'Tallennettu paikkaan {}.', 'Zapisano w slocie {}.', 'Uloženo do slotu {}.', 'Αποθηκεύτηκε στη θέση {}.',
        'Сохранено в слот {}.', '{}. yuvaya kaydedildi.'),
    'Saved.': R('Opgeslagen.', 'Gemt.', 'Lagret.', 'Sparat.', 'Tallennettu.', 'Zapisano.', 'Uloženo.',
                'Αποθηκεύτηκε.', 'Сохранено.', 'Kaydedildi.'),
    'This is now your story save.': R(
        'Dit is nu je verhaalopslag.', 'Dette er nu din historiegemning.', 'Dette er nå historielagringen din.',
        'Detta är nu din berättelsesparfil.', 'Tämä on nyt tarinatallennuksesi.', 'To jest teraz twój zapis fabularny.',
        'Toto je nyní vaše příběhová pozice.', 'Αυτή είναι πλέον η αποθήκευση ιστορίας σας.',
        'Теперь это ваше сюжетное сохранение.', 'Bu artık hikâye kaydınız.'),
    'That slot is empty.': R(
        'Dat slot is leeg.', 'Den plads er tom.', 'Den plassen er tom.', 'Den platsen är tom.', 'Se paikka on tyhjä.',
        'Ten slot jest pusty.', 'Tento slot je prázdný.', 'Αυτή η θέση είναι κενή.', 'Этот слот пуст.',
        'Bu yuva boş.'),
    'Could not write the load request.': R(
        'Kon het laadverzoek niet schrijven.', 'Kunne ikke skrive anmodningen om indlæsning.',
        'Kunne ikke skrive forespørselen om innlasting.', 'Kunde inte skriva begäran om inläsning.',
        'Latauspyyntöä ei voitu kirjoittaa.', 'Nie udało się zapisać żądania wczytania.',
        'Požadavek na načtení se nepodařilo zapsat.', 'Δεν ήταν δυνατή η εγγραφή του αιτήματος φόρτωσης.',
        'Не удалось записать запрос на загрузку.', 'Yükleme isteği yazılamadı.'),
    'Practice mode is only for Uncharted 1, 2 and 3.': R(
        'De oefenmodus is alleen voor Uncharted 1, 2 en 3.', 'Øvetilstand findes kun til Uncharted 1, 2 og 3.',
        'Øvingsmodus finnes bare for Uncharted 1, 2 og 3.', 'Övningsläget finns bara för Uncharted 1, 2 och 3.',
        'Harjoitustila on vain Uncharted 1, 2 ja 3 -peleille.', 'Tryb treningowy jest tylko dla Uncharted 1, 2 i 3.',
        'Tréninkový režim je jen pro Uncharted 1, 2 a 3.', 'Η λειτουργία εξάσκησης είναι μόνο για τα Uncharted 1, 2 και 3.',
        'Режим тренировки есть только для Uncharted 1, 2 и 3.', 'Alıştırma modu yalnızca Uncharted 1, 2 ve 3 içindir.'),
    'Could not start practice mode: {}': R(
        'Kon de oefenmodus niet starten: {}', 'Kunne ikke starte øvetilstand: {}', 'Kunne ikke starte øvingsmodus: {}',
        'Kunde inte starta övningsläget: {}', 'Harjoitustilaa ei voitu käynnistää: {}',
        'Nie udało się włączyć trybu treningowego: {}', 'Tréninkový režim se nepodařilo spustit: {}',
        'Δεν ήταν δυνατή η έναρξη της λειτουργίας εξάσκησης: {}', 'Не удалось запустить режим тренировки: {}',
        'Alıştırma modu başlatılamadı: {}'),
    'Going to {}...': R(
        'Naar {}...', 'Går til {}...', 'Går til {}...', 'Går till {}...', 'Siirrytään: {}...', 'Przechodzenie do: {}...',
        'Přechod na: {}...', 'Μετάβαση σε: {}...', 'Переход: {}...', '{} konumuna gidiliyor...'),
    'Nothing to keep yet: the game has not saved since the jump.': R(
        'Nog niets om te houden: de game heeft sinds de sprong niet opgeslagen.',
        'Intet at beholde endnu: spillet har ikke gemt siden springet.',
        'Ingenting å beholde ennå: spillet har ikke lagret siden hoppet.',
        'Inget att behålla än: spelet har inte sparat sedan hoppet.',
        'Ei vielä mitään säilytettävää: peli ei ole tallentanut hypyn jälkeen.',
        'Nie ma jeszcze czego zachować: gra nie zapisywała od skoku.',
        'Zatím není co ponechat: hra od skoku neukládala.',
        'Τίποτα για διατήρηση ακόμη: το παιχνίδι δεν έχει αποθηκεύσει από το άλμα.',
        'Пока нечего сохранять: игра не сохранялась после перехода.',
        'Henüz korunacak bir şey yok: oyun atlamadan beri kaydetmedi.'),
    'Could not write the request.': R(
        'Kon het verzoek niet schrijven.', 'Kunne ikke skrive anmodningen.', 'Kunne ikke skrive forespørselen.',
        'Kunde inte skriva begäran.', 'Pyyntöä ei voitu kirjoittaa.', 'Nie udało się zapisać żądania.',
        'Požadavek se nepodařilo zapsat.', 'Δεν ήταν δυνατή η εγγραφή του αιτήματος.', 'Не удалось записать запрос.',
        'İstek yazılamadı.'),
    'an unknown checkpoint': R(
        'een onbekend checkpoint', 'et ukendt checkpoint', 'et ukjent sjekkpunkt', 'en okänd kontrollpunkt',
        'tuntematon tarkistuspiste', 'nieznany punkt kontrolny', 'neznámý kontrolní bod', 'άγνωστο σημείο ελέγχου',
        'неизвестная контрольная точка', 'bilinmeyen bir kontrol noktası'),
    'no save yet': R(
        'nog geen opslag', 'ingen gemning endnu', 'ingen lagring ennå', 'ingen sparfil än', 'ei vielä tallennusta',
        'brak zapisu', 'zatím žádná pozice', 'καμία αποθήκευση ακόμη', 'сохранения пока нет', 'henüz kayıt yok'),
    'Checkpoint {}': R(
        'Checkpoint {}', 'Checkpoint {}', 'Sjekkpunkt {}', 'Kontrollpunkt {}', 'Tarkistuspiste {}',
        'Punkt kontrolny {}', 'Kontrolní bod {}', 'Σημείο ελέγχου {}', 'Контрольная точка {}', 'Kontrol noktası {}'),
    'Cutscene': R('Tussenfilmpje', 'Mellemsekvens', 'Mellomsekvens', 'Mellansekvens', 'Välivideo', 'Przerywnik',
                  'Animace', 'Σκηνή', 'Ролик', 'Ara sahne'),
    'Chapter {}': R(
        'Hoofdstuk {}', 'Kapitel {}', 'Kapittel {}', 'Kapitel {}', 'Luku {}', 'Rozdział {}', 'Kapitola {}',
        'Κεφάλαιο {}', 'Глава {}', 'Bölüm {}'),
}
