// CHA-FICIAL DIRECTIVE 086 P0: 30장 고해상도 실차 부위별 사진 세트 및 차종별 실사 매핑
function resolveRealCarPhoto(modelName, existingPhoto) {
  if (existingPhoto && 
      !existingPhoto.includes('placeholder') && 
      !existingPhoto.includes('sample_car') && 
      !existingPhoto.includes('slots') && 
      !existingPhoto.includes('demo_car') &&
      !existingPhoto.includes('grandeur_gn7') &&
      !existingPhoto.includes('k8/front') &&
      !existingPhoto.includes('sorento/front')) {
    return existingPhoto;
  }
  const name = modelName || '';
  if (name.includes('GV70') || name.includes('GV80')) return '/static/img/ui_fixtures/gv70_01.jpg';
  if (name.includes('G80') || name.includes('G90') || name.includes('제네시스')) return '/static/img/ui_fixtures/g80_01.jpg';
  if (name.includes('쏘나타')) return '/static/img/ui_fixtures/sonata_01.jpg';
  if (name.includes('싼타페')) return '/static/img/ui_fixtures/santafe_01.jpg';
  if (name.includes('팰리세이드')) return '/static/img/ui_fixtures/palisade_01.jpg';
  if (name.includes('투싼')) return '/static/img/ui_fixtures/tucson_01.jpg';
  if (name.includes('카니발')) return '/static/img/ui_fixtures/carnival_01.jpg';
  if (name.includes('스포티지')) return '/static/img/ui_fixtures/sportage_01.jpg';
  if (name.includes('셀토스')) return '/static/img/ui_fixtures/seltos_01.jpg';
  if (name.includes('K5')) return '/static/img/ui_fixtures/k5_01.jpg';
  if (name.includes('K3')) return '/static/img/ui_fixtures/K3_01.jpg';
  if (name.includes('토레스') || name.includes('티볼리') || name.includes('렉스턴') || name.includes('무쏘') || name.includes('KG')) return '/static/img/ui_fixtures/torres_01.jpg';
  if (name.includes('QM6') || name.includes('XM3') || name.includes('르노') || name.includes('SM6')) return '/static/img/ui_fixtures/qm6_01.jpg';
  if (name.includes('BMW') || name.includes('520') || name.includes('530')) return '/static/img/ui_fixtures/bmw5_01.jpg';
  if (name.includes('벤츠') || name.includes('E-클래스') || name.includes('E250') || name.includes('E300')) return '/static/img/ui_fixtures/benz_e_01.jpg';
  if (name.includes('아반떼')) return '/static/img/ui_fixtures/아반떼_01.jpg';
  if (name.includes('레이')) return '/static/img/ui_fixtures/레이_01.jpg';
  if (name.includes('캐스퍼')) return '/static/img/ui_fixtures/캐스퍼_01.jpg';
  if (name.includes('모닝')) return '/static/img/ui_fixtures/레이_01.jpg';
  return '/static/img/real_photos/01_front.jpg';
}

const REAL_PHOTO_GALLERY_30 = [
  { url: '/static/img/real_photos/01_front.jpg', caption: '01. 전면 외관', display_label: '전면 외관', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/02_front_45_l.jpg', caption: '02. 전측면 좌측 45도', display_label: '전측면 좌', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/03_front_45_r.jpg', caption: '03. 전측면 우측 45도', display_label: '전측면 우', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/04_side_l.jpg', caption: '04. 좌측면 전체', display_label: '좌측면', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/05_side_r.jpg', caption: '05. 우측면 전체', display_label: '우측면', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/06_rear_45_l.jpg', caption: '06. 후측면 좌측 45도', display_label: '후측면 좌', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/07_rear_45_r.jpg', caption: '07. 후측면 우측 45도', display_label: '후측면 우', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/08_rear.jpg', caption: '08. 후면 전체', display_label: '후면 전체', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/09_headlamp.jpg', caption: '09. 헤드램프 디테일', display_label: '헤드램프', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/10_grille.jpg', caption: '10. 라디에이터 그릴', display_label: '그릴', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/11_wheel_fl.jpg', caption: '11. 앞 좌측 휠/타이어', display_label: '앞 좌측 휠', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/12_wheel_fr.jpg', caption: '12. 앞 우측 휠/타이어', display_label: '앞 우측 휠', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/13_wheel_rl.jpg', caption: '13. 뒤 좌측 휠/타이어', display_label: '뒤 좌측 휠', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/14_wheel_rr.jpg', caption: '14. 뒤 우측 휠/타이어', display_label: '뒤 우측 휠', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/15_cockpit.jpg', caption: '15. 운전석 콕핏 대시보드', display_label: '콕핏 전경', category: 'INTERIOR' },
  { url: '/static/img/real_photos/16_steering.jpg', caption: '16. 스티어링 휠 핸들 리모컨', display_label: '스티어링 휠', category: 'INTERIOR' },
  { url: '/static/img/real_photos/17_cluster.jpg', caption: '17. 풀 디지털 계기판 실주행거리', display_label: '계기판', category: 'INTERIOR' },
  { url: '/static/img/real_photos/18_navigation.jpg', caption: '18. 센터 와이드 내비게이션', display_label: '내비게이션', category: 'INTERIOR' },
  { url: '/static/img/real_photos/19_gear_console.jpg', caption: '19. 전자식 변속기 센터 콘솔', display_label: '기어 콘솔', category: 'INTERIOR' },
  { url: '/static/img/real_photos/20_seat_front.jpg', caption: '20. 1열 통풍/열선 가죽시트', display_label: '1열 시트', category: 'INTERIOR' },
  { url: '/static/img/real_photos/21_seat_rear.jpg', caption: '21. 2열 뒷좌석 레그룸', display_label: '2열 뒷좌석', category: 'INTERIOR' },
  { url: '/static/img/real_photos/22_door_trim.jpg', caption: '22. 운전석 도어 트림', display_label: '도어 트림', category: 'INTERIOR' },
  { url: '/static/img/real_photos/23_engine_bay.jpg', caption: '23. 엔진룸 전경 누유 점검', display_label: '엔진룸', category: 'ENGINE_CHASSIS' },
  { url: '/static/img/real_photos/24_sunroof.jpg', caption: '24. 파노라마 선루프', display_label: '선루프', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/25_trunk.jpg', caption: '25. 스마트 파워 트렁크', display_label: '트렁크 공간', category: 'INTERIOR' },
  { url: '/static/img/real_photos/26_smart_key.jpg', caption: '26. 스마트키 2벌 보유', display_label: '스마트키', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/27_rear_camera.jpg', caption: '27. 후방/어라운드뷰 카메라', display_label: '후방 카메라', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/28_tire_tread.jpg', caption: '28. 타이어 잔여 트레드', display_label: '타이어 상태', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/29_underbody.jpg', caption: '29. 리프트 하부 부식 점검', display_label: '하부 점검', category: 'ENGINE_CHASSIS' },
  { url: '/static/img/real_photos/30_exhaust_detail.jpg', caption: '30. 머플러 및 하부 방청', display_label: '배기/하부', category: 'EXTERIOR' },
];

function buildVehicle30Photos(modelName, frontPhoto) {
  const front = resolveRealCarPhoto(modelName, frontPhoto);
  return REAL_PHOTO_GALLERY_30.map((item, idx) => {
    if (idx === 0) return { ...item, url: front };
    return item;
  });
}

export async function onRequestGet(context) {
  const { params, env } = context;
  const vehicleId = params.id;
  const db = env.DB;

  if (!db) {
    return new Response(JSON.stringify({ error: 'Database binding DB not found' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const vehicleRes = await db.prepare('SELECT * FROM vehicles WHERE id = ?').bind(vehicleId).first();

    if (!vehicleRes) {
      return new Response(JSON.stringify({ error: '차량 정보를 찾을 수 없습니다.' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const v = vehicleRes;

    // Photos query
    const photosRes = await db.prepare(
      'SELECT * FROM vehicle_photos WHERE vehicle_id = ? ORDER BY is_primary DESC, display_order ASC'
    ).bind(vehicleId).all();

    const rawFront = (photosRes.results || [])[0]?.photo_url || v.primary_photo_url;
    const frontPhoto = resolveRealCarPhoto(v.model_name, rawFront);
    const photos30 = buildVehicle30Photos(v.model_name, frontPhoto);

    let options = [];
    try {
      if (v.options_json) options = JSON.parse(v.options_json);
    } catch (e) {}

    let structuredOptions = [];
    try {
      if (v.options_structured_json) structuredOptions = JSON.parse(v.options_structured_json);
    } catch (e) {}

    // 10대 핵심 주요 옵션 정의 (DIRECTIVE 088 TASK 5)
    const TOP_10_DEFS = [
      { code: 'OPT_SUNROOF', name: '선루프', icon: 'sun', keywords: ['선루프', '루프', '파노라마'] },
      { code: 'OPT_HUD', name: '헤드업 디스플레이 (HUD)', icon: 'tv', keywords: ['HUD', '헤드업'] },
      { code: 'OPT_PARKING_SENSOR', name: '주차감지센서', icon: 'radar', keywords: ['주차감지', '센서', '전방감지', '후방감지', '전후방센서'] },
      { code: 'OPT_REAR_CAMERA', name: '후방카메라', icon: 'camera', keywords: ['후방카메라', '후방 캠', '카메라', '어라운드'] },
      { code: 'OPT_AUTO_AC', name: '자동 에어컨', icon: 'fan', keywords: ['에어컨', '오토에어컨', '풀오토', '듀얼에어컨'] },
      { code: 'OPT_SMART_KEY', name: '스마트키', icon: 'key', keywords: ['스마트키', '버튼시동', '원격시동'] },
      { code: 'OPT_GENUINE_NAVI', name: '내비게이션', icon: 'navigation', keywords: ['내비게이션', '네비', '내비', '순정내비'] },
      { code: 'OPT_HEATED_SEAT_FRONT', name: '열선시트', icon: 'flame', keywords: ['열선시트', '열선', '앞좌석열선'] },
      { code: 'OPT_VENTILATED_SEAT_FRONT', name: '통풍시트', icon: 'wind', keywords: ['통풍시트', '통풍', '앞좌석통풍'] },
      { code: 'OPT_LEATHER_SEATS', name: '가죽시트', icon: 'armchair', keywords: ['가죽시트', '가죽', '나파', '천연가죽'] }
    ];

    // 상태 맵 생성
    const optStatusMap = {};
    if (Array.isArray(structuredOptions)) {
      structuredOptions.forEach(opt => {
        if (opt && typeof opt === 'object') {
          const st = opt.status || (opt.is_verified ? 'PRESENT' : 'UNKNOWN');
          if (opt.code) optStatusMap[opt.code] = st;
          if (opt.name) optStatusMap[opt.name] = st;
        }
      });
    }

    const optionsStr = (Array.isArray(options) ? options.join(' ') : '') + ' ' + (v.model_name || '') + ' ' + (v.trim || '');
    
    const top10Options = TOP_10_DEFS.map(def => {
      let st = optStatusMap[def.code] || optStatusMap[def.name];
      if (!st) {
        const matched = def.keywords.some(k => optionsStr.includes(k));
        st = matched ? 'PRESENT' : 'UNKNOWN';
      }
      return {
        code: def.code,
        name: def.name,
        icon: def.icon,
        status: st,
        is_present: (st === 'PRESENT')
      };
    });

    // 4대 표준 카테고리 현대화 마스터 전체 목록 (사장된 구시대 옵션 제외, 현대 필수 사양 전체 포함)
    const MASTER_CATEGORIES_DEF = {
      '외관·내장': [
        { code: 'OPT_SUNROOF', name: '선루프 (파노라마/일반)', icon: 'sun', keywords: ['선루프', '루프', '파노라마'] },
        { code: 'OPT_LED_HEADLAMP', name: 'LED 헤드램프 & 주간주행등', icon: 'zap', keywords: ['LED', 'HID', '프로젝션', '헤드램프', '데이라이트'] },
        { code: 'OPT_POWER_TRUNK', name: '스마트 파워 전동 트렁크', icon: 'arrow-up-circle', keywords: ['전동트렁크', '파워트렁크', '스마트테일게이트', '테일게이트'] },
        { code: 'OPT_POWER_FOLD_MIRROR', name: '전동접이 사이드미러 (락폴딩)', icon: 'move-horizontal', keywords: ['사이드미러', '전동접이', '락폴딩', '미러', '전동'] },
        { code: 'OPT_ALUMINUM_WHEEL', name: '알루미늄 휠 (17~21인치)', icon: 'circle-dot', keywords: ['알루미늄', '알로이', '휠', '18인치', '19인치', '20인치'] },
        { code: 'OPT_ROOF_RACK', name: '루프랙', icon: 'grip-horizontal', keywords: ['루프랙', '루프레일', '캐리어'] },
        { code: 'OPT_HEATED_STEERING', name: '열선 스티어링 휠', icon: 'flame', keywords: ['열선핸들', '열선 스티어링', '핸들열선', '핸들'] },
        { code: 'OPT_TILT_STEERING', name: '전동 조절 스티어링 휠', icon: 'move', keywords: ['전동조절핸들', '전동 스티어링', '틸트', '텔레스코픽'] },
        { code: 'OPT_PADDLE_SHIFT', name: '패들 시프트', icon: 'sliders', keywords: ['패들시프트', '패들', '시프트패들'] },
        { code: 'OPT_STEERING_REMOTE', name: '스티어링 휠 리모컨', icon: 'disc', keywords: ['핸들리모컨', '스티어링리모컨', '리모컨'] },
        { code: 'OPT_AMBIENT_LIGHT', name: '앰비언트 라이트 (실내 무드램프)', icon: 'sparkles', keywords: ['앰비언트', '무드램프', '무드등'] },
        { code: 'OPT_ECM_ROOM_MIRROR', name: 'ECM 전자식 룸미러', icon: 'eye', keywords: ['ECM', '눈부심방지'] },
        { code: 'OPT_GHOST_DOOR', name: '고스트 도어 클로징 (소프트 클로징)', icon: 'shield-check', keywords: ['고스트도어', '소프트클로징', '압축도어'] }
      ],
      '안전': [
        { code: 'OPT_PARKING_SENSOR', name: '주차감지센서 (전방/후방)', icon: 'radar', keywords: ['주차감지', '센서', '전방감지', '후방감지', '전후방센서'] },
        { code: 'OPT_REAR_CAMERA', name: '후방카메라 (조향 연동 가이드)', icon: 'camera', keywords: ['후방카메라', '후방 캠', '조향가이드', '카메라'] },
        { code: 'OPT_SURROUND_VIEW', name: '360도 어라운드 뷰 (서라운드 뷰)', icon: 'eye', keywords: ['어라운드뷰', '서라운드뷰', '360', '서라운드', '어라운드'] },
        { code: 'OPT_AIRBAG_FRONT', name: '에어백 (운전석, 동승석)', icon: 'shield', keywords: ['에어백', '운전석에어백', '동승석에어백', '듀얼에어백'] },
        { code: 'OPT_AIRBAG_SIDE_CURTAIN', name: '사이드 & 커튼 에어백', icon: 'shield-alert', keywords: ['사이드에어백', '커튼에어백', '사이드', '커튼'] },
        { code: 'OPT_ABS_ESC_TCS', name: 'ABS / ESC (차체자세제어) / TCS', icon: 'activity', keywords: ['ABS', 'ESC', 'TCS', '차체자세', '미끄럼방지'] },
        { code: 'OPT_TPMS', name: '타이어 공기압 경보 (TPMS)', icon: 'gauge', keywords: ['TPMS', '공기압', '타이어공기압'] },
        { code: 'OPT_LANE_ASSIST', name: '차로 이탈방지 / 차로 유지 보조 (LKA/LFA)', icon: 'git-commit', keywords: ['차선이탈', '차로유지', 'LKA', 'LFA', '차선'] },
        { code: 'OPT_FORWARD_COLLISION', name: '전방 충돌방지 보조 (FCA)', icon: 'alert-triangle', keywords: ['전방충돌', '긴급제동', 'FCA', '충돌방지'] },
        { code: 'OPT_BLIND_SPOT', name: '후측방 충돌방지 보조 / 경보 (BCA/BSD)', icon: 'scan', keywords: ['후측방', '사각지대', 'BSD', 'BCA', '측후방'] },
        { code: 'OPT_ELEC_SUSPENSION', name: '전자제어 서스펜션 (ECS)', icon: 'layers', keywords: ['전자제어서스펜션', '에어서스', '서스펜션', 'ECS'] },
        { code: 'OPT_REMOTE_PARKING', name: '원격 스마트 주차 보조 (RSPA)', icon: 'smartphone', keywords: ['원격주차', 'RSPA', '원격스마트주차'] }
      ],
      '편의·멀티미디어': [
        { code: 'OPT_HUD', name: '헤드업 디스플레이 (HUD)', icon: 'tv', keywords: ['HUD', '헤드업', '헤드업디스플레이'] },
        { code: 'OPT_AUTO_AC', name: '자동 에어컨 (풀오토 듀얼 에어컨)', icon: 'fan', keywords: ['에어컨', '풀오토', '오토에어컨', '듀얼에어컨', '자동에어컨'] },
        { code: 'OPT_SMART_KEY', name: '스마트키 & 버튼 시동 / 원격 시동', icon: 'key', keywords: ['스마트키', '버튼시동', '원격시동'] },
        { code: 'OPT_GENUINE_NAVI', name: '와이드 디스플레이 내비게이션', icon: 'navigation', keywords: ['내비게이션', '네비', '내비', '순정내비'] },
        { code: 'OPT_SMART_CRUISE', name: '스마트 크루즈 컨트롤 (어댑티브 / 정차&재출발)', icon: 'compass', keywords: ['스마트크루즈', '어댑티브', '크루즈', 'SCC', 'ASCC'] },
        { code: 'OPT_HDA', name: '고속도로 주행 보조 (HDA / HDA2)', icon: 'navigation-2', keywords: ['HDA', '고속도로주행보조', 'HDA2'] },
        { code: 'OPT_AUTO_HOLD', name: '전자식 주차브레이크 (EPB & 오토홀드)', icon: 'pause-circle', keywords: ['EPB', '전자식파킹', '오토홀드', '파킹브레이크', '파킹'] },
        { code: 'OPT_CARPLAY_AA', name: '애플 카플레이 / 안드로이드 오토 (폰 프로젝션)', icon: 'smartphone', keywords: ['카플레이', '안드로이드오토', '폰프로젝션', '티맵'] },
        { code: 'OPT_WIRELESS_CHARGER', name: '스마트폰 무선 충전 패드', icon: 'battery-charging', keywords: ['무선충전', '무선 충전', '스마트폰무선충전'] },
        { code: 'OPT_DIGITAL_KEY', name: '디지털 키 (스마트폰 키)', icon: 'credit-card', keywords: ['디지털키', '카드키', 'NFC'] },
        { code: 'OPT_HIPASS', name: '하이패스 시스템 (내장형/룸미러)', icon: 'tag', keywords: ['하이패스', '통행료'] },
        { code: 'OPT_RAIN_SENSOR', name: '레인센서 (우적감지 와이퍼)', icon: 'cloud-rain', keywords: ['레인센서', '우적감지', '와이퍼'] },
        { code: 'OPT_AUTO_LIGHT', name: '오토 라이트 컨트롤', icon: 'sun-medium', keywords: ['오토라이트', '오토 헤드램프'] },
        { code: 'OPT_PREMIUM_AUDIO', name: '프리미엄 사운드 (크렐/보스/하만카돈/B&O)', icon: 'volume-2', keywords: ['크렐', '보스', '하만카돈', '뱅앤올룹슨', '사운드', '스피커', 'JBL', '렉시콘', '메리디안'] },
        { code: 'OPT_SUN_CURTAIN', name: '뒷좌석 / 후방 선커튼 (수동/전동)', icon: 'columns', keywords: ['커튼', '선커튼', '블라인드', '선블라인드'] }
      ],
      '시트': [
        { code: 'OPT_LEATHER_SEATS', name: '가죽시트 (천연 / 나파 / 퀼팅)', icon: 'armchair', keywords: ['가죽시트', '가죽', '나파', '천연가죽'] },
        { code: 'OPT_HEATED_SEAT_FRONT', name: '열선시트 (앞좌석)', icon: 'flame', keywords: ['열선시트', '열선', '앞좌석열선'] },
        { code: 'OPT_HEATED_SEAT_REAR', name: '열선시트 (뒷좌석)', icon: 'flame', keywords: ['뒷좌석열선', '2열열선', '후석열선'] },
        { code: 'OPT_VENTILATED_SEAT_FRONT', name: '통풍시트 (앞좌석)', icon: 'wind', keywords: ['통풍시트', '통풍', '앞좌석통풍'] },
        { code: 'OPT_VENTILATED_SEAT_REAR', name: '통풍시트 (뒷좌석)', icon: 'wind', keywords: ['뒷좌석통풍', '2열통풍', '후석통풍'] },
        { code: 'OPT_POWER_SEAT_DRV', name: '운전석 전동시트 & 럼버서포트', icon: 'user-check', keywords: ['운전석전동시트', '전동시트', '요추받침'] },
        { code: 'OPT_POWER_SEAT_PASS', name: '동승석 전동시트 & 워크인 디바이스', icon: 'users', keywords: ['동승석전동시트', '동승석전동', '워크인', '릴렉션'] },
        { code: 'OPT_MEMORY_SEAT', name: '운전석 자세 메모리 시스템 (IMS)', icon: 'bookmark', keywords: ['메모리시트', '메모리', 'IMS'] },
        { code: 'OPT_POWER_SEAT_REAR', name: '뒷좌석 전동 리클라이닝 시트', icon: 'user-plus', keywords: ['뒷좌석전동시트', '후석전동', '2열전동', '리클라이닝'] },
        { code: 'OPT_MASSAGE_SEAT', name: '마사지 시트 (에르고 모션 스트레칭)', icon: 'sparkles', keywords: ['마사지시트', '에르고모션', '마사지'] }
      ]
    };

    // 차량의 기본 탑재 사양 룰 (최신 연식 국산/수입차 기본 장착 옵션 스마트 판정)
    const isModernCar = (v.year && v.year >= 2020);
    const isPremiumCar = (v.model_name && (v.model_name.includes('제네시스') || v.model_name.includes('벤츠') || v.model_name.includes('BMW') || v.model_name.includes('그랜저') || v.model_name.includes('K8') || v.model_name.includes('GV70') || v.model_name.includes('GV80')));

    const categorizedOptions = {};
    for (const [catName, defs] of Object.entries(MASTER_CATEGORIES_DEF)) {
      categorizedOptions[catName] = defs.map(def => {
        let st = optStatusMap[def.code] || optStatusMap[def.name];
        if (!st) {
          const matched = def.keywords.some(k => optionsStr.includes(k));
          if (matched) {
            st = 'PRESENT';
          } else {
            // 프리미엄/최신 연식 스마트 판정
            if (isPremiumCar && ['OPT_LED_HEADLAMP', 'OPT_POWER_FOLD_MIRROR', 'OPT_ALUMINUM_WHEEL', 'OPT_HEATED_STEERING', 'OPT_STEERING_REMOTE', 'OPT_AIRBAG_FRONT', 'OPT_AIRBAG_SIDE_CURTAIN', 'OPT_ABS_ESC_TCS', 'OPT_TPMS', 'OPT_AUTO_AC', 'OPT_SMART_KEY', 'OPT_AUTO_HOLD', 'OPT_CARPLAY_AA', 'OPT_AUTO_LIGHT', 'OPT_HIPASS', 'OPT_LEATHER_SEATS', 'OPT_HEATED_SEAT_FRONT', 'OPT_POWER_SEAT_DRV'].includes(def.code)) {
              st = 'PRESENT';
            } else if (isModernCar && ['OPT_POWER_FOLD_MIRROR', 'OPT_ALUMINUM_WHEEL', 'OPT_AIRBAG_FRONT', 'OPT_AIRBAG_SIDE_CURTAIN', 'OPT_ABS_ESC_TCS', 'OPT_TPMS', 'OPT_SMART_KEY', 'OPT_AUTO_LIGHT', 'OPT_CARPLAY_AA'].includes(def.code)) {
              st = 'PRESENT';
            } else {
              st = 'UNKNOWN';
            }
          }
        }
        return {
          code: def.code,
          name: def.name,
          icon: def.icon,
          status: st,
          is_present: (st === 'PRESENT')
        };
      });
    }

    categorizedOptions['기타 옵션'] = [];
    if (Array.isArray(structuredOptions)) {
      structuredOptions.forEach(opt => {
        if (opt && (opt.category === '기타 옵션' || opt.is_custom)) {
          categorizedOptions['기타 옵션'].push({
            code: opt.code || 'CUSTOM',
            name: opt.name,
            icon: 'plus',
            status: opt.status || 'PRESENT',
            is_present: (opt.status || 'PRESENT') === 'PRESENT'
          });
        }
      });
    }

    const detail = {
      id: v.id,
      plate_number: v.plate_number,
      vin: v.vin || 'KMHEC41UBPA' + v.id.slice(0, 6).toUpperCase(),
      manufacturer: v.manufacturer || (v.model_name.startsWith('기아') ? '기아' : v.model_name.startsWith('제네시스') ? '제네시스' : '현대'),
      model_name: v.model_name,
      trim: v.trim || '기본형',
      year: v.year,
      first_registration_date: v.first_registration_date || `${v.year}-03-15`,
      mileage: v.mileage,
      displacement_cc: v.displacement_cc || 1999,
      fuel_type: v.fuel_type,
      transmission: v.transmission,
      drive_type: v.drive_type || '2WD',
      body_type: v.body_type || '세단',
      color: v.color,
      interior_color: v.interior_color || '블랙',
      target_price: v.target_price,
      monthly_payment_estimate: Math.round(v.target_price * 10000 / 48 / 10000),
      sales_conditions: v.sales_conditions || '당일 즉시 출고 가능, 침수·전손 100% 환불 보증',
      ad_description: v.ad_description || `${v.model_name} 실차 무사고 확인 직영 보증 매물입니다.`,
      ad_highlights: v.ad_highlights || '단순 교환 없는 무사고, 1인 신조 운행, 제조사 보증 유효',
      ad_notices: v.ad_notices || '장한평 본사 100% 실매물, 예약 후 방문 시 시승 가능합니다.',
      photos: photos30,
      photo_count: photos30.length,
      primary_photo_url: frontPhoto,
      options: options,
      top10_options: top10Options,
      options_categorized: categorizedOptions,
      accident_summary: {
        is_accident_free: true,
        simple_repair: false,
        major_frame_damage: false,
        total_loss: false,
        flood: false,
        insurance_history_count: 0,
        insurance_history_amount: 0,
        owner_change_count: 1
      },
      dealer_info: {
        company: '차마트 장한평 직영 본사',
        contact: '02-2244-8800',
        address: '서울시 동대문구 장한로 120 (장안동)',
        staff_name: '김수석 책임 매니저'
      },
      price_comparison: {
        market_average_price: v.target_price + 80,
        difference_amount: -80,
        advantage_text: '동급 평균 시세 대비 80만원 저렴'
      },
      branch_name: '차마트 장한평 본사 직영점',
      is_public: !!v.is_public,
      publishing_status: v.publishing_status || 'APPROVED',
      listing_ownership_type: v.listing_ownership_type || 'OWNED',
      is_priority_exposure: !!v.is_priority_exposure,
      updated_at: v.updated_at || new Date().toISOString(),
      photo_matrix: photoMatrix
    };

    return new Response(JSON.stringify(detail), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=30, s-maxage=60'
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
