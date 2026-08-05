/* Bili Vote Tracker — 纯逻辑模块（无 DOM 依赖，可被 node --test 直接测试）
 * UMD: 浏览器挂 window, Node 走 module.exports */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.BVTLogic = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // 候选人 → 头像文件编号映射（B站活动 API items 顺序）
  const HERO_IDS = {
    迪迦: 1, 梦比优斯: 2, 雷欧: 3, 捷德: 4, 布莱泽: 5, 戴拿: 6,
    奈克赛斯: 7, 盖亚: 8, 银河: 9, 欧布: 10, 赛罗: 11, 泽塔: 12,
    艾克斯: 13, 泰迦: 14, 希卡利: 15, 提欧: 16, 高斯: 17,
    特利迦: 18, 阿古茹: 19, 麦克斯: 20, 格丽乔: 21, 奥特之王: 22,
    爱迪: 23, 阿斯特拉: 24, 维克特利: 25, 斯科特: 26, 罗索: 27,
    亚刻: 28, 奥美迦: 29, 布鲁: 30, 风马: 31, 德凯: 32,
    雷古洛思: 33, 杰斯提斯: 34, 葛雷特: 35, 杰诺: 36, 尼奥斯: 37,
    利布特: 38, 贝丝: 39, 乔尼亚斯: 40, 哉阿斯: 41, 帕瓦德: 42,
    尤莉安: 43, 查克: 44, 泰塔斯: 45, 纳伊斯: 46,
  };

  // 千分位格式化
  function fmt(n) {
    return Number(n || 0).toLocaleString();
  }

  function dateFmt(s) {
    return s ? new Date(s).toLocaleString() : '-';
  }

  // 候选人全名 → 头像资源路径（无映射返回 ''）
  function heroSrc(t) {
    const n = HERO_IDS[String(t || '').replace('奥特曼', '')];
    return n ? `/assets/heroes/ultraman_${String(n).padStart(2, '0')}.png` : '';
  }

  // 排序：票数从大到小；票数相同按中文名 localeCompare 稳定排序
  function rankSort(a, b) {
    const d = (b.votes || 0) - (a.votes || 0);
    return d !== 0 ? d : String(a.title || '').localeCompare(String(b.title || ''), 'zh');
  }

  // diff 增量格式化：null/undefined/非数 → '-'; 0/-0 → 灰色 0; 正负带样式
  function fmtDelta(v) {
    if (v === null || v === undefined) return '-';
    const n = Number(v);
    if (!Number.isFinite(n)) return '-';
    if (n === 0 || Object.is(n, -0)) return '<span class="delta-flat">0</span>';
    const sign = n > 0 ? '+' : '';
    const cls = n > 0 ? 'delta-up' : 'delta-down';
    return `<span class="${cls}">${sign}${fmt(n)}</span>`;
  }

  // 国家代码 → emoji 国旗（ISO 3166-1 alpha-2）
  function countryCodeToFlag(code) {
    if (!code || typeof code !== 'string' || code.length !== 2) return '';
    const upper = code.toUpperCase();
    // 两个字母各自偏移到区域指示符，拼成完整国旗 emoji
    return String.fromCodePoint((upper.charCodeAt(0) - 65) + 0x1F1E6) +
           String.fromCodePoint((upper.charCodeAt(1) - 65) + 0x1F1E6);
  }

  return { HERO_IDS, fmt, dateFmt, heroSrc, rankSort, fmtDelta, countryCodeToFlag };
});
