/**
 * PATCHNOTES.md 에서 현재 package.json 버전 섹션을 추출해 stdout에 출력.
 * GitHub Release body 생성용.
 */
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const notes = fs.readFileSync(path.join(root, 'PATCHNOTES.md'), 'utf8');
const version = pkg.version;

const headingRe = /^##\s+v?(.+)$/gm;
const matches = [...notes.matchAll(headingRe)];
let body = '';

for (let i = 0; i < matches.length; i += 1) {
  const ver = matches[i][1].trim().split(/\s+—\s+|\s+-\s+/)[0].trim();
  if (ver === version || ver === `v${version}`) {
    const start = matches[i].index;
    const end = i + 1 < matches.length ? matches[i + 1].index : notes.length;
    body = notes.slice(start, end).trim();
    break;
  }
}

if (!body) {
  body = `## v${version}\n\n- 자세한 내용은 PATCHNOTES.md 를 참고하세요.`;
}

process.stdout.write(`${body}\n`);
