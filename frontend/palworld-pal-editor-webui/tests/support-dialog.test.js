import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const readSource = path => readFile(new URL(path, import.meta.url), "utf8").catch(() => "");

test("support methods reveal details before opening links or a closable full-size QR dialog", async () => {
  const [dialog, app, entry, packageJson] = await Promise.all([
    readSource("../src/components/SupportDialog.vue"),
    readSource("../src/App.vue"),
    readSource("../src/views/EntryView.vue"),
    readSource("../package.json"),
  ]);

  assert.match(dialog, /role="dialog"/);
  assert.match(dialog, /selectedMethod/);
  assert.match(dialog, /@click="selectedMethod = method\.id"/);
  assert.match(dialog, /class="support-payment-detail"/);
  assert.match(dialog, /expandedQr/);
  assert.match(dialog, /class="support-qr-overlay"/);
  assert.match(dialog, /@click\.self="closeQr"/);
  assert.match(dialog, /@keydown\.esc\.stop="closeQr"/);
  assert.match(dialog, /class="support-qr-crop support-qr-crop--compact"/);
  assert.match(dialog, /https:\/\/ko-fi\.com\/connlost/);
  assert.match(dialog, /https:\/\/www\.paypal\.com\/paypalme\/c0nnlost/);
  assert.match(dialog, /qr: ['"]\/support\/alipay\.png['"]/);
  assert.match(dialog, /qr: ['"]\/support\/wechat-pay\.png['"]/);
  assert.match(dialog, /https:\/\/discord\.gg\/FnuA95nMJ8/);
  assert.match(dialog, /https:\/\/github\.com\/KrisCris\/Palworld-Pal-Editor\/issues/);
  assert.doesNotMatch(dialog, /<details/);
  assert.doesNotMatch(dialog, /afdian/i);

  assert.match(app, /import SupportDialog from ['"]@\/components\/SupportDialog\.vue['"]/);
  assert.match(app, /<SupportDialog/);
  assert.doesNotMatch(app, /MarkdownModal/);
  assert.match(entry, /@click="palStore\.SHOW_DONATE_FLAG = true"/);
  assert.doesNotMatch(entry, /keep_this_project_alive\.md/);
  assert.equal(JSON.parse(packageJson).dependencies.marked, undefined);
});
