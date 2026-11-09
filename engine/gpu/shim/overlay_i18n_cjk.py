# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
# The in-game menu in Korean (ko) and Traditional Chinese (zh: the launcher's zh-Hant). Wording follows the launcher's
# (launcher/ui/i18n/ko.json, zh-Hant.json). Checkpoint names and chapter titles are the games' own and stay English.
# The menu draws them with Windows' own fonts (Malgun Gothic, Microsoft JhengHei: bbport_overlay.cpp).

LANGUAGES = ('ko', 'zh')


def R(ko, zh):
    return dict(zip(LANGUAGES, (ko, zh)))


MENU = {
    '%.0f FPS  (%.1f ms)   1%% low %.0f': R('%.0f FPS  (%.1f ms)   하위 1%% %.0f', '%.0f FPS  (%.1f ms)   最低 1%% %.0f'),
    '(Balanced)': R('(균형)', '(平衡)'),
    '(Performance)': R('(성능)', '(效能)'),
    '(Quality)': R('(품질)', '(品質)'),
    '(native)': R('(기본)', '(原生)'),
    '(now)': R('(현재)', '(目前)'),
    "(the game's own)": R('(게임 기본)', '(遊戲原本)'),
    'Anti-aliasing': R('안티에일리어싱', '反鋸齒'),
    'Apply and restart the game': R('적용하고 게임 다시 시작', '套用並重新啟動遊戲'),
    'Before the last load: %s%s': R('마지막 불러오기 전: %s%s', '上次載入前: %s%s'),
    'Bronze trophy earned': R('브론즈 트로피 획득', '獲得銅獎盃'),
    'Cancel': R('취소', '取消'),
    'Changes apply after restarting the game': R('변경 사항은 게임을 다시 시작한 후 적용됩니다', '變更會在重新啟動遊戲後套用'),
    "Changes here apply at once, for this session. The launcher's settings apply each time the game starts: set the "
    "same there to keep a change.": R(
        '여기서 바꾼 내용은 바로 적용되며 이번 세션에만 유지됩니다. 런처 설정은 게임을 시작할 때마다 적용되니, 변경을 '
        '유지하려면 런처에서도 똑같이 설정하세요.',
        '這裡的變更會立即套用，只限這次遊玩。啟動器的設定在每次啟動遊戲時套用：要保留變更，請在啟動器中做相同設定。'),
    'Chapter': R('챕터', '章節'),
    'Chapter {}': R('챕터 {}', '第 {} 章'),
    'Character motion vectors': R('캐릭터 모션 벡터', '角色動態向量'),
    'Checkpoint jumps are not available for this release of the game.': R(
        '이 버전의 게임에서는 체크포인트 이동을 사용할 수 없습니다.', '這個版本的遊戲無法跳到檢查點。'),
    'Checkpoint jumps do not work with this release of the game.': R(
        '이 버전의 게임에서는 체크포인트 이동이 작동하지 않습니다.', '跳到檢查點在這個版本的遊戲中無法運作。'),
    'Checkpoint {}': R('체크포인트 {}', '檢查點 {}'),
    'Checkpoints': R('체크포인트', '檢查點'),
    'Close': R('닫기', '關閉'),
    'Close the game': R('게임 닫기', '關閉遊戲'),
    'Close the game? Progress since the last save is lost.': R(
        '게임을 닫을까요? 마지막 저장 이후의 진행 상황은 사라집니다.', '要關閉遊戲嗎？上次存檔後的進度將會遺失。'),
    'Controller: Cross (A) = OK, Circle (B) = cancel': R(
        '컨트롤러: × 버튼 (A) = 확인, ○ 버튼 (B) = 취소', '控制器: ×鍵 (A) = 確定，○鍵 (B) = 取消'),
    "Copies of this game's campaign save (the one Continue loads). Treasures, unlocks and trophies are not changed.": R(
        '이 게임의 캠페인 저장 데이터(이어하기가 불러오는 것)의 사본입니다. 보물, 잠금 해제 항목, 트로피는 바뀌지 않습니다.',
        '這款遊戲戰役存檔（「繼續」載入的那個）的副本。寶物、解鎖項目與獎盃不會改變。'),
    'Could not copy the save: {}': R('저장 데이터를 복사하지 못했습니다: {}', '無法複製存檔: {}'),
    'Could not start practice mode: {}': R('연습 모드를 시작하지 못했습니다: {}', '無法開始練習模式: {}'),
    'Could not write the load request.': R('불러오기 요청을 기록하지 못했습니다.', '無法寫入載入要求。'),
    'Could not write the request.': R('요청을 기록하지 못했습니다.', '無法寫入要求。'),
    'Cutscene': R('컷신', '過場動畫'),
    'Delete or Triangle (Y): delete this save': R('Delete 또는 △ 버튼 (Y): 이 저장 데이터 삭제', 'Delete 或 △鍵 (Y): 刪除這個存檔'),
    'Delete save': R('저장 데이터 삭제', '刪除存檔'),
    'Developer options': R('개발자 옵션', '開發人員選項'),
    'Done.': R('완료했습니다.', '完成。'),
    'Each frame the scene shifts by a fraction of a pixel and the anti-aliasing gathers detail from several frames. '
    'Off: smoothing from the history only.': R(
        '프레임마다 장면을 1픽셀보다 작게 옮기고, 안티에일리어싱이 여러 프레임에서 디테일을 모읍니다. 끄기: 이전 프레임만으로 '
        '부드럽게 합니다.',
        '每一幀畫面都會移動不到一個像素，反鋸齒會從多個幀收集細節。關閉: 只用歷史幀平滑。'),
    'El Dorado — settings  (Insert / L3+R3)': R('El Dorado — 설정  (Insert / L3+R3)', 'El Dorado — 設定  (Insert / L3+R3)'),
    'Exact vectors for animated objects (applies after restarting the game).': R(
        '움직이는 물체의 정확한 벡터 (게임을 다시 시작한 후 적용).', '動畫物件的精確向量（重新啟動遊戲後套用）。'),
    'FPS counter in the corner': R('구석에 FPS 표시', '角落的 FPS 計數器'),
    'FSR 3 (any graphics card)': R('FSR 3 (모든 그래픽 카드)', 'FSR 3 (任何顯示卡)'),
    'FSR 4 unavailable: %s': R('FSR 4 사용 불가: %s', '無法使用 FSR 4: %s'),
    'FSR 4: auto exposure': R('FSR 4: 자동 노출', 'FSR 4: 自動曝光'),
    'FSR 4: inverted jitter sign': R('FSR 4: 지터 부호 반전', 'FSR 4: 反轉抖動符號'),
    'Finding the shaders in your game files (only this once) %.1f / %.1f GB%s': R(
        '게임 파일에서 셰이더를 찾는 중 (이번 한 번만) %.1f / %.1f GB%s', '正在從遊戲檔案中尋找著色器（只有這一次） %.1f / %.1f GB%s'),
    'Finishing...': R('마무리하는 중...', '正在完成...'),
    'Follows your playthrough as you play on.': R('계속 플레이하면 진행에 맞춰 따라갑니다.', '繼續遊玩時會跟著你的進度。'),
    'Frame generation': R('프레임 생성', '畫格生成'),
    'Frame time graph': R('프레임 타임 그래프', '畫格時間圖'),
    "Generated frames between the game's own: 60 FPS on screen becomes 120. Adds a little input latency; menus and "
    "cutscene videos are not generated. The launcher's Frame rate limit counts generated frames.": R(
        '게임 자체 프레임 사이에 프레임을 생성합니다: 화면의 60 FPS가 120이 됩니다. 입력 지연이 약간 늘어나며, 메뉴와 컷신 '
        '영상은 생성되지 않습니다. 런처의 프레임 레이트 제한은 생성된 프레임도 셉니다.',
        '在遊戲原本的畫格之間生成畫格：畫面上的 60 FPS 變成 120。會稍微增加輸入延遲；選單與過場影片不會生成。啟動器的'
        '畫面更新率上限會把生成的畫格算進去。'),
    'Mouse': R('마우스', '滑鼠'),
    'Mouse sensitivity': R('마우스 감도', '滑鼠靈敏度'),
    'Aiming sensitivity': R('조준 감도', '瞄準靈敏度'),
    'Vertical sensitivity': R('상하 감도', '垂直靈敏度'),
    'Aiming: times the mouse sensitivity while aiming (1.00 the same as looking around). Vertical: times it for '
    'up and down. Ctrl+click to type a value.': R(
        '조준: 조준 중 마우스 감도의 배율입니다(1.00은 둘러볼 때와 같음). 상하: 위아래 움직임의 배율입니다. '
        'Ctrl+클릭으로 값을 입력합니다.',
        '瞄準：瞄準時滑鼠靈敏度的倍率(1.00 與環顧四周相同)。垂直：上下移動的倍率。按 Ctrl+點擊可輸入數值。'),
    'Or double-click a checkpoint in the list.': R('또는 목록의 체크포인트를 더블클릭하세요.', '或在清單中按兩下檢查點。'),
    'Go there': R('이동', '前往'),
    'Going to {}...': R('{}(으)로 이동하는 중...', '正在前往 {}...'),
    'Gold trophy earned': R('골드 트로피 획득', '獲得金獎盃'),
    'If a large shader cache causes problems, clear it in the launcher:': R(
        '셰이더 캐시가 커서 문제가 생기면 런처에서 지우세요:', '如果龐大的著色器快取造成問題，請在啟動器中清除：'),
    'Jumping turns on practice mode: until the game restarts, it saves to a practice copy, not to your own save.': R(
        '이동하면 연습 모드가 켜집니다: 게임을 다시 시작할 때까지 내 저장 데이터가 아닌 연습용 사본에 저장합니다.',
        '跳轉會開啟練習模式：在遊戲重新啟動前，會存到練習用副本，而不是你自己的存檔。'),
    'Keep playing': R('계속 플레이', '繼續遊玩'),
    'Keep this progress': R('이 진행 상황 유지', '保留這個進度'),
    'Key letters': R('키 글자', '按鍵字母'),
    'Keyboard: type, Backspace to erase, Enter = OK, Esc = cancel': R(
        '키보드: 입력, Backspace로 지우기, Enter = 확인, Esc = 취소', '鍵盤: 輸入，Backspace 刪除，Enter = 確定，Esc = 取消'),
    'Load': R('불러오기', '載入'),
    'Load game': R('게임 불러오기', '載入遊戲'),
    'Load slot {}? The game restarts and Continue starts there. Your current save is kept as "Before the last load".': R(
        '슬롯 {}을(를) 불러올까요? 게임이 다시 시작되고 이어하기가 거기서 시작됩니다. 현재 저장 데이터는 "마지막 불러오기 전"으로 '
        '보관됩니다.',
        '要載入欄位 {} 嗎？遊戲會重新啟動，「繼續」會從那裡開始。你目前的存檔會保留為「上次載入前」。'),
    'Load story save': R('스토리 저장 불러오기', '載入劇情存檔'),
    'Load the save from before the last load? The game restarts and Continue starts there. Your current save is kept '
    'as "Before the last load".': R(
        '마지막 불러오기 전의 저장 데이터를 불러올까요? 게임이 다시 시작되고 이어하기가 거기서 시작됩니다. 현재 저장 데이터는 '
        '"마지막 불러오기 전"으로 보관됩니다.',
        '要載入上次載入前的存檔嗎？遊戲會重新啟動，「繼續」會從那裡開始。你目前的存檔會保留為「上次載入前」。'),
    'Load the story save? The game restarts and Continue starts there. Your current save is kept as "Before the last '
    'load".': R(
        '스토리 저장을 불러올까요? 게임이 다시 시작되고 이어하기가 거기서 시작됩니다. 현재 저장 데이터는 "마지막 불러오기 전"으로 '
        '보관됩니다.',
        '要載入劇情存檔嗎？遊戲會重新啟動，「繼續」會從那裡開始。你目前的存檔會保留為「上次載入前」。'),
    'Loading': R('불러오는 중', '載入中'),
    'Make the practice save your save? The game restarts and Continue starts there. Your save from before is kept as '
    '"Before the last load".': R(
        '연습용 저장을 내 저장 데이터로 만들까요? 게임이 다시 시작되고 이어하기가 거기서 시작됩니다. 이전 저장 데이터는 '
        '"마지막 불러오기 전"으로 보관됩니다.',
        '要把練習存檔變成你的存檔嗎？遊戲會重新啟動，「繼續」會從那裡開始。你之前的存檔會保留為「上次載入前」。'),
    'Make this my story save': R('이것을 스토리 저장으로', '設為我的劇情存檔'),
    'Make your current save the story save?': R('현재 저장 데이터를 스토리 저장으로 만들까요?', '要把目前的存檔設為劇情存檔嗎？'),
    'Marks transparent effects (particles, haze) so the upscaler relies less on past frames: fewer trails behind '
    'effects, more shimmer under them.': R(
        '투명한 효과(파티클, 안개)를 표시해 업스케일러가 지난 프레임에 덜 의존하게 합니다: 효과 뒤의 잔상은 줄고, 그 아래의 '
        '깜빡임은 늘어납니다.',
        '標記透明效果（粒子、霧氣），讓升頻器較少依賴過去的畫格：效果後方的殘影較少，下方的閃爍較多。'),
    'Mask maximum': R('마스크 최댓값', '遮罩最大值'),
    'Mask scale': R('마스크 배율', '遮罩比例'),
    'Mask threshold': R('마스크 임계값', '遮罩臨界值'),
    'Multiplier': R('배수', '倍數'),
    'New save': R('새 저장 데이터', '新存檔'),
    'Nothing to keep yet: the game has not saved since the jump.': R(
        '아직 유지할 것이 없습니다: 이동한 뒤 게임이 저장하지 않았습니다.', '還沒有可保留的內容：跳轉後遊戲尚未存檔。'),
    'Nothing to save yet: the game has not saved since the jump.': R(
        '아직 저장할 것이 없습니다: 이동한 뒤 게임이 저장하지 않았습니다.', '還沒有可存的內容：跳轉後遊戲尚未存檔。'),
    'Now: %s': R('현재: %s', '目前: %s'),
    'Off': R('끄기', '關閉'),
    "Off (the game's own)": R('끄기 (게임 기본)', '關閉（遊戲原本）'),
    'Other': R('기타', '其他'),
    'Picture': R('화면', '畫面'),
    'Platinum trophy earned': R('플래티넘 트로피 획득', '獲得白金獎盃'),
    'Practice mode is only for Uncharted 1, 2 and 3.': R(
        '연습 모드는 Uncharted 1, 2, 3 전용입니다.', '練習模式只適用於 Uncharted 1、2 和 3。'),
    'Practice mode: the game saves to a practice copy until you restart it. Your own save and story save are not '
    'touched.': R(
        '연습 모드: 게임을 다시 시작할 때까지 연습용 사본에 저장합니다. 내 저장 데이터와 스토리 저장은 건드리지 않습니다.',
        '練習模式：在你重新啟動遊戲前，遊戲會存到練習用副本。你自己的存檔與劇情存檔不會被更動。'),
    'Preparing pipelines': R('파이프라인 준비 중', '正在準備管線'),
    'Preparing pipelines %u / %u%s': R('파이프라인 준비 중 %u / %u%s', '正在準備管線 %u / %u%s'),
    'Preparing shaders': R('셰이더 준비 중', '正在準備著色器'),
    'Preparing shaders %u / %u%s': R('셰이더 준비 중 %u / %u%s', '正在準備著色器 %u / %u%s'),
    'Press Delete or Triangle (Y) AGAIN to delete this save (it goes to savedata-deleted)': R(
        '이 저장 데이터를 삭제하려면 Delete 또는 △ 버튼 (Y)을 한 번 더 누르세요 (savedata-deleted로 이동)',
        '再按一次 Delete 或 △鍵 (Y) 刪除這個存檔（會移到 savedata-deleted）'),
    'Reactive mask': R('반응형 마스크', '反應遮罩'),
    'Red/green: horizontal/vertical motion (8 pixels = full brightness); blue: an exact object vector.': R(
        '빨강/초록: 가로/세로 움직임 (8픽셀 = 최대 밝기); 파랑: 물체의 정확한 벡터.', '紅/綠: 水平/垂直移動（8 像素 = 最大亮度）；藍: 物件的精確向量。'),
    'Rendering %s': R('렌더링: %s', '算繪: %s'),
    'Replace what slot {} holds with your current save?': R(
        '슬롯 {}의 내용을 현재 저장 데이터로 바꿀까요?', '要用目前的存檔取代欄位 {} 的內容嗎？'),
    'SETTINGS > GAME FILES > Clear shader cache': R('설정 > 게임 파일 > 셰이더 캐시 지우기', '設定 > 遊戲檔案 > 清除著色器快取'),
    'Save game': R('게임 저장', '儲存遊戲'),
    'Save here': R('여기에 저장', '存在這裡'),
    'Save slots': R('저장 슬롯', '存檔欄位'),
    'Save slots are only for Uncharted 1, 2 and 3.': R('저장 슬롯은 Uncharted 1, 2, 3 전용입니다.', '存檔欄位只適用於 Uncharted 1、2 和 3。'),
    'Saved in slot {}.': R('슬롯 {}에 저장했습니다.', '已存到欄位 {}。'),
    'Saved.': R('저장했습니다.', '已儲存。'),
    'Screenshot saved': R('스크린샷을 저장했습니다', '已儲存截圖'),
    'Select a save, then Delete or Triangle (Y) to delete it': R(
        '저장 데이터를 고른 뒤 Delete 또는 △ 버튼 (Y)으로 삭제', '選擇一個存檔，再按 Delete 或 △鍵 (Y) 刪除'),
    'Set in the launcher (Display: Render resolution); it applies when the game starts. Quality, Balanced and '
    'Performance render smaller and let the anti-aliasing (DLSS or FSR) rebuild the full size: Uncharted 3 only.': R(
        '런처에서 설정합니다 (디스플레이: 렌더링 해상도). 게임을 시작할 때 적용됩니다. 품질, 균형, 성능은 더 작게 렌더링하고 '
        '안티에일리어싱(DLSS 또는 FSR)이 원래 크기로 재구성합니다: Uncharted 3 전용.',
        '在啟動器中設定（顯示：算繪解析度）；在遊戲啟動時套用。品質、平衡與效能會以較小尺寸算繪，再由反鋸齒（DLSS 或 FSR）'
        '重建成完整大小：只限 Uncharted 3。'),
    'Settings': R('설정', '設定'),
    'Sharpening pass': R('선명화 처리', '銳利化處理'),
    "Sharpens the anti-aliased picture (AMD RCAS, also with DLSS). 0 is off; the launcher's Low, Medium and High are "
    "0.2, 0.4 and 0.7. Ctrl+click to type a value.": R(
        '안티에일리어싱된 화면을 선명하게 합니다 (AMD RCAS, DLSS에서도). 0은 끄기이며, 런처의 낮음, 중간, 높음은 0.2, 0.4, '
        '0.7입니다. Ctrl+클릭으로 값을 입력할 수 있습니다.',
        '讓反鋸齒後的畫面更銳利（AMD RCAS，DLSS 也適用）。0 為關閉；啟動器的低、中、高分別是 0.2、0.4 和 0.7。Ctrl+'
        '點擊可輸入數值。'),
    'Sharpness': R('선명도', '銳利度'),
    'Show the mask': R('마스크 표시', '顯示遮罩'),
    'Show the motion vectors': R('모션 벡터 표시', '顯示動態向量'),
    'Silver trophy earned': R('실버 트로피 획득', '獲得銀獎盃'),
    'Slots': R('슬롯', '欄位'),
    'Smooths edges and keeps the picture stable from frame to frame; with an upscaled render resolution it also '
    'rebuilds the full size. DLSS needs a GeForce RTX card.': R(
        '가장자리를 부드럽게 하고 프레임 간 화면을 안정적으로 유지합니다. 업스케일 렌더링 해상도에서는 원래 크기로 재구성도 '
        '합니다. DLSS는 GeForce RTX 카드가 필요합니다.',
        '讓邊緣平滑，並讓畫面在畫格之間保持穩定；使用升頻的算繪解析度時，也會重建完整大小。DLSS 需要 GeForce RTX 顯示卡。'),
    'Starting...': R('시작하는 중...', '正在開始...'),
    "Starts with a movie: use Chapter Select in the game's menu.": R(
        '영상으로 시작합니다: 게임 메뉴의 챕터 선택을 사용하세요.', '以影片開始：請使用遊戲選單中的章節選擇。'),
    "Starts with the game's next save.": R('게임이 다음에 저장할 때 시작합니다.', '從遊戲的下一次存檔開始。'),
    'Step 1 of 2: building shaders from your game files': R(
        '2단계 중 1단계: 게임 파일로 셰이더를 만드는 중', '步驟 1/2：正在從遊戲檔案建立著色器'),
    'Step 1 of 2: finding the shaders in your game files (only this once)': R(
        '2단계 중 1단계: 게임 파일에서 셰이더를 찾는 중 (이번 한 번만)', '步驟 1/2：正在從遊戲檔案中尋找著色器（只有這一次）'),
    'Step 1 of 2: loading shaders': R('2단계 중 1단계: 셰이더를 불러오는 중', '步驟 1/2：正在載入著色器'),
    'Step 2 of 2: compiling them for your graphics card': R(
        '2단계 중 2단계: 그래픽 카드에 맞게 컴파일하는 중', '步驟 2/2：正在為你的顯示卡編譯'),
    'Story save': R('스토리 저장', '劇情存檔'),
    'Sub-pixel jitter': R('서브픽셀 지터', '次像素抖動'),
    'That slot is empty.': R('그 슬롯은 비어 있습니다.', '那個欄位是空的。'),
    'The game is saving: try again in a moment.': R('게임이 저장 중입니다: 잠시 후 다시 시도하세요.', '遊戲正在存檔：請稍後再試。'),
    'The letters on the key pictures in the game: English (US), or one of the keyboards installed in Windows. The keys '
    'work by their place either way. Kept for the next starts.': R(
        '게임 속 키 그림의 글자: English (US) 또는 Windows에 설치된 키보드 중 하나. 어느 쪽이든 키는 위치로 작동합니다. '
        '다음 시작에도 유지됩니다.',
        '遊戲中按鍵圖示上的字母：English (US)，或 Windows 中安裝的其中一種鍵盤。無論哪種，按鍵都依位置運作。下次啟動仍會沿用。'),
    'The mode selected above is active. FSR 4 can be selected again.': R(
        '위에서 고른 모드가 켜져 있습니다. FSR 4를 다시 고를 수 있습니다.', '上方選擇的模式已啟用。可以再次選擇 FSR 4。'),
    'There is no campaign save yet.': R('아직 캠페인 저장 데이터가 없습니다.', '還沒有戰役存檔。'),
    'This checkpoint is not in this release of the game.': R(
        '이 체크포인트는 이 버전의 게임에 없습니다.', '這個檢查點不在這個版本的遊戲中。'),
    'This happens once, before your first launch. Later launches start straight away.': R(
        '첫 실행 전에 한 번만 진행됩니다. 이후 실행은 바로 시작됩니다.', '這只會在第一次啟動前進行一次。之後的啟動會立即開始。'),
    'This is now your story save.': R('이제 이것이 스토리 저장입니다.', '這現在是你的劇情存檔。'),
    'To carry on from here for real (for example past a place that does not work): the game restarts and Continue '
    'starts at the practice save, which becomes your save and your story save. Your save from before is kept in Save '
    'slots as "Before the last load".': R(
        '여기서부터 실제로 계속하려면 (예를 들어 작동하지 않는 곳을 지난 뒤): 게임이 다시 시작되고 이어하기가 연습용 저장에서 '
        '시작되며, 그것이 내 저장 데이터와 스토리 저장이 됩니다. 이전 저장 데이터는 저장 슬롯에 "마지막 불러오기 전"으로 '
        '보관됩니다.',
        '要真正從這裡繼續（例如越過無法運作的地方後）：遊戲會重新啟動，「繼續」會從練習存檔開始，它會成為你的存檔與劇情存檔。'
        '你之前的存檔會以「上次載入前」保留在存檔欄位中。'),
    "Top line, the game's own frames: FPS and frame time, 1%L the average of the slowest 1% (stutter), MAX the "
    "slowest frame (last 5 seconds). Below: the anti-aliasing, the render size (Q, B, P: Quality, Balanced, "
    "Performance) and with frame generation FG, the frames on screen. The graph: the game's frame times, a spike is "
    "a hitch.": R(
        '윗줄은 게임 자체 프레임: FPS와 프레임 타임, 1%L은 가장 느린 1%의 평균(끊김), MAX는 가장 느린 프레임(최근 5초). '
        '아래: 안티에일리어싱, 렌더링 크기(Q, B, P: 품질, 균형, 성능), 프레임 생성 시 FG와 화면의 프레임. 그래프: 게임의 '
        '프레임 타임이며, 튀어나온 부분은 끊김입니다.',
        '第一行是遊戲原本的畫格：FPS 與畫格時間，1%L 是最慢 1% 的平均（卡頓），MAX 是最慢的畫格（最近 5 秒）。下方：反鋸齒、'
        '算繪尺寸（Q、B、P：品質、平衡、效能），以及畫格生成時的 FG 與畫面上的畫格。圖表：遊戲的畫格時間，突起就是卡頓。'),
    'Up/Down or D-pad: choose   Enter or Cross (A): OK   Esc or Circle (B): cancel': R(
        '위/아래 또는 방향키: 선택   Enter 또는 × 버튼 (A): 확인   Esc 또는 ○ 버튼 (B): 취소',
        '上/下或方向鍵: 選擇   Enter 或 ×鍵 (A): 確定   Esc 或 ○鍵 (B): 取消'),
    'Use this after skipping ahead on purpose: the story save then follows your playthrough from where you are now.': R(
        '일부러 앞으로 건너뛴 뒤에 사용하세요: 그러면 스토리 저장이 지금 위치부터 진행을 따라갑니다.',
        '在刻意跳到後面之後使用：劇情存檔就會從你現在的位置跟著你的進度。'),
    'Yes': R('예', '是'),
    'Yes, keep it': R('예, 유지', '是，保留'),
    'Your graphics driver is compiling the shaders again (after a driver update or when its cache was cleared). The '
    'game continues when this is done.': R(
        '그래픽 드라이버가 셰이더를 다시 컴파일하고 있습니다 (드라이버 업데이트 후 또는 캐시를 지운 경우). 끝나면 게임이 '
        '계속됩니다.',
        '你的顯示卡驅動程式正在重新編譯著色器（在驅動程式更新後或快取被清除時）。完成後遊戲會繼續。'),
    'Your save has moved away from your story (Chapter Select or a new game). The story save stays here until you load '
    'it, or make the current save your story save to keep the change.': R(
        '저장 데이터가 스토리에서 벗어났습니다 (챕터 선택 또는 새 게임). 스토리 저장은 불러올 때까지 여기 남으며, 변경을 '
        '유지하려면 현재 저장 데이터를 스토리 저장으로 만드세요.',
        '你的存檔已偏離劇情（章節選擇或新遊戲）。劇情存檔會留在這裡直到你載入它；或把目前的存檔設為劇情存檔以保留變更。'),
    'a few seconds left': R('몇 초 남음', '剩下幾秒'),
    'about {:.0f} min left': R('약 {:.0f}분 남음', '大約剩下 {:.0f} 分鐘'),
    'about {:.0f} s left': R('약 {:.0f}초 남음', '大約剩下 {:.0f} 秒'),
    'about {} min {} s left': R('약 {}분 {}초 남음', '大約剩下 {} 分 {} 秒'),
    'about {} s left': R('약 {}초 남음', '大約剩下 {} 秒'),
    'an unknown checkpoint': R('알 수 없는 체크포인트', '未知的檢查點'),
    'empty': R('비어 있음', '空'),
    'no save yet': R('아직 저장 없음', '尚無存檔'),
    '— not supported by this graphics card': R('— 이 그래픽 카드에서는 지원되지 않음', '— 這張顯示卡不支援'),
}
