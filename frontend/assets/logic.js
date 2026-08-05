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

  // 候选人 → 头像文件编号映射（按 item_id 稳定编号，不随排名变动；2026-08-06 修复错位）
const HERO_IDS = {
    泽塔: 1,
    银河: 2,
    奥特之王: 3,
    泰迦: 4,
    贝丝: 5,
    奈克赛斯: 6,
    纳伊斯: 7,
    布鲁: 8,
    爱迪: 9,
    葛雷特: 10,
    特利迦: 11,
    雷古洛思: 12,
    利布特: 13,
    杰斯提斯: 14,
    梦比优斯: 15,
    斯科特: 16,
    亚刻: 17,
    维克特利: 18,
    尼奥斯: 19,
    布莱泽: 20,
    捷德: 21,
    艾克斯: 22,
    高斯: 23,
    阿古茹: 24,
    戴拿: 25,
    提欧: 26,
    泰塔斯: 27,
    查克: 28,
    迪迦: 29,
    风马: 30,
    德凯: 31,
    奥美迦: 32,
    尤莉安: 33,
    格丽乔: 34,
    帕瓦德: 35,
    希卡利: 36,
    哉阿斯: 37,
    雷欧: 38,
    欧布: 39,
    乔尼亚斯: 40,
    阿斯特拉: 41,
    杰诺: 42,
    罗索: 43,
    赛罗: 44,
    麦克斯: 45,
    盖亚: 46,
  };

  // 千分位格式化
  function fmt(n) {
    return Number(n || 0).toLocaleString();
  }

  function dateFmt(s) {
    return s ? new Date(s).toLocaleString() : '-';
  }

  // 候选人全名 → 头像资源路径（无映射返回 ''）；?v= 用于 cache-bust（发版时更新）
  const ASSET_VERSION = "1.1.2";
  function heroSrc(t) {
    const n = HERO_IDS[String(t || '').replace('奥特曼', '')];
    return n ? `/assets/heroes/ultraman_${String(n).padStart(2, '0')}.png?v=${ASSET_VERSION}` : '';
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
