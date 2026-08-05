/* Bili Vote Tracker — 核心纯逻辑单元测试
 * 运行: node --test frontend/logic.test.js （Node 22+ 内置 test runner，零依赖） */
const test = require('node:test');
const assert = require('node:assert/strict');
const L = require('./assets/logic.js');

// ---------- HERO_IDS / heroSrc ----------
test('HERO_IDS 覆盖全部 46 位候选人', () => {
  assert.equal(Object.keys(L.HERO_IDS).length, 46, '应为 46 位候选映射');
  assert.equal(L.HERO_IDS['迪迦'], 29);   // 按 item_id 稳定编号
  assert.equal(L.HERO_IDS['泽塔'], 1);
  assert.equal(L.HERO_IDS['纳伊斯'], 7);
});

test('heroSrc 返回正确头像路径（补零）', () => {
  assert.equal(L.heroSrc('迪迦奥特曼'), '/assets/heroes/ultraman_29.png?v=1.1.2');
  assert.equal(L.heroSrc('麦克斯奥特曼'), '/assets/heroes/ultraman_45.png?v=1.1.2');
  assert.equal(L.heroSrc('奥特之王'), '/assets/heroes/ultraman_03.png?v=1.1.2');
  assert.equal(L.heroSrc('纳伊斯奥特曼'), '/assets/heroes/ultraman_07.png?v=1.1.2');
  assert.equal(L.heroSrc('泽塔奥特曼'), '/assets/heroes/ultraman_01.png?v=1.1.2');
});

test('heroSrc 未知候选返回空串', () => {
  assert.equal(L.heroSrc('哥斯拉'), '');
  assert.equal(L.heroSrc(''), '');
  assert.equal(L.heroSrc(null), '');
});

test('heroSrc 处理无"奥特曼"后缀的名字', () => {
  assert.equal(L.heroSrc('迪迦'), '/assets/heroes/ultraman_29.png?v=1.1.2');
});

// ---------- rankSort ----------
test('rankSort 按票数从大到小', () => {
  const rows = [
    { title: 'B', votes: 100 },
    { title: 'A', votes: 500 },
    { title: 'C', votes: 300 },
  ];
  const sorted = rows.slice().sort(L.rankSort);
  assert.deepEqual(sorted.map(r => r.title), ['A', 'C', 'B']);
});

test('rankSort 票数相同按中文名 localeCompare 稳定', () => {
  const rows = [
    { title: '银河奥特曼', votes: 100 },
    { title: '盖亚奥特曼', votes: 100 },
    { title: '欧布奥特曼', votes: 100 },
  ];
  const sorted = rows.slice().sort(L.rankSort);
  // zh localeCompare: 盖亚(ga) < 欧布(ou) < 银河(yin)
  assert.deepEqual(sorted.map(r => r.title), ['盖亚奥特曼', '欧布奥特曼', '银河奥特曼']);
});

test('rankSort 缺 votes 视为 0', () => {
  const rows = [{ title: 'A' }, { title: 'B', votes: 10 }];
  const sorted = rows.slice().sort(L.rankSort);
  assert.equal(sorted[0].title, 'B');
});

// ---------- fmt ----------
test('fmt 千分位', () => {
  assert.equal(L.fmt(1234567), '1,234,567');
  assert.equal(L.fmt(0), '0');
  assert.equal(L.fmt(null), '0');
});

// ---------- fmtDelta ----------
test('fmtDelta: null/undefined/非数 → "-"', () => {
  assert.equal(L.fmtDelta(null), '-');
  assert.equal(L.fmtDelta(undefined), '-');
  assert.equal(L.fmtDelta('abc'), '-');
});

test('fmtDelta: 0/-0 → 灰色 flat 0', () => {
  assert.equal(L.fmtDelta(0), '<span class="delta-flat">0</span>');
  assert.equal(L.fmtDelta(-0), '<span class="delta-flat">0</span>');
});

test('fmtDelta: 正增量带 + 前缀和 delta-up', () => {
  assert.equal(L.fmtDelta(1234), '<span class="delta-up">+1,234</span>');
});

test('fmtDelta: 负增量 delta-down', () => {
  assert.equal(L.fmtDelta(-50), '<span class="delta-down">-50</span>');
});

// ---------- countryCodeToFlag ----------
test('countryCodeToFlag 正确 emoji 国旗', () => {
  assert.equal(L.countryCodeToFlag('CN'), '🇨🇳');
  assert.equal(L.countryCodeToFlag('JP'), '🇯🇵');
  assert.equal(L.countryCodeToFlag('us'), '🇺🇸'); // 小写也可
});

test('countryCodeToFlag 无效输入返回空串', () => {
  assert.equal(L.countryCodeToFlag(''), '');
  assert.equal(L.countryCodeToFlag('XYZ'), '');
  assert.equal(L.countryCodeToFlag(null), '');
});
