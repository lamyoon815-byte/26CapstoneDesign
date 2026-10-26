// PERSONGAL 서버 연동 공통 모듈. 모든 페이지가 이 파일 하나로 로컬 서버와 통신한다.
// [명세 대기] API 명세가 정해지면 BASE와 PATHS만 채운다. 비어 있는 API는 요청을 보내지 않는다(API.ready로 확인).
var API = (function () {
  // 로컬 서버 주소. 화면 파일을 같은 서버가 띄워 주면 빈 값 그대로 둔다 (예: 'http://localhost:8080')
  var BASE = '';

  // 화면에서 쓰는 API 이름 → 경로. 경로 안의 {id} 같은 자리는 params로 채운다
  var PATHS = {
    login: '',          // 로그인
    signup: '',         // 회원가입
    me: '',             // 로그인 상태 확인
    orders: '',         // 내 구매 목록
    review: '',         // 리뷰 저장 (구매 제품 {id})
    profile: '',        // 내 톤, 피할 성분, 잘 맞는 성분
    avoid: '',          // 피할 성분 추가·삭제
    suspects: '',       // 의심 성분 목록 (성분별 포함 제품)
    recommend: '',      // 맞춤 추천 제품
    cart: '',           // 장바구니 목록·수량·삭제
    cartWarnings: '',   // 장바구니 성분 경고
    diagnose: '',       // 퍼스널컬러 진단 (사진 업로드)
    toneProducts: '',   // 톤별 제품
    homeProducts: ''    // 홈: 내 퍼스널컬러·내 피부에 맞는 상품
  };

  function ready(name) { return !!PATHS[name]; }

  function url(name, params) {
    return BASE + PATHS[name].replace(/\{(\w+)\}/g, function (_, k) { return encodeURIComponent(params && params[k] != null ? params[k] : ''); });
  }

  // 요청 하나. 실패하면 화면에 보여줄 문장을 담은 Error를 던진다
  function request(name, opt) {
    opt = opt || {};
    if (!ready(name)) return Promise.reject(new Error('아직 서버와 연결되지 않은 기능이에요.'));
    var init = { method: opt.method || 'GET', credentials: 'include', headers: {} };
    if (opt.body instanceof FormData) init.body = opt.body; // 사진 업로드는 FormData 그대로
    else if (opt.body != null) { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(opt.body); }
    return fetch(url(name, opt.params), init).then(function (res) {
      return res.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
        if (!res.ok) {
          var err = new Error((data && data.message) || (res.status === 401 ? '로그인이 필요해요.' : '요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.'));
          err.status = res.status;
          throw err;
        }
        return data;
      });
    }, function () {
      throw new Error('서버에 연결할 수 없어요. 로컬 서버가 켜져 있는지 확인해 주세요.');
    });
  }

  // 목록 자리에 상태를 표시한다: 'load' 불러오는 중 / 'err' 실패(다시 시도 버튼) / 'empty' 비어 있음 / 숨기기
  function state(el, kind, msg, retry) {
    if (!kind) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    el.className = 'state ' + kind;
    el.setAttribute('role', kind === 'err' ? 'alert' : 'status');
    el.textContent = msg || (kind === 'load' ? '불러오는 중이에요.' : kind === 'empty' ? '아직 내용이 없어요.' : '불러오지 못했어요.');
    if (kind === 'err' && retry) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'retry'; b.textContent = '다시 시도';
      b.addEventListener('click', retry);
      el.appendChild(document.createElement('br'));
      el.appendChild(b);
    }
  }

  return {
    ready: ready,
    get: function (name, params) { return request(name, { params: params }); },
    post: function (name, body, params) { return request(name, { method: 'POST', body: body, params: params }); },
    put: function (name, body, params) { return request(name, { method: 'PUT', body: body, params: params }); },
    del: function (name, params) { return request(name, { method: 'DELETE', params: params }); },
    state: state
  };
})();
