import assert from "node:assert/strict";
import test from "node:test";

import { formatStorageLabel } from "../src/components/pal-storage-label.js";
import en from "../src/i18n/en.js";
import zhCN from "../src/i18n/zh-CN.js";

const translator = messages => (key, args = []) => args.reduce(
  (text, value, index) => text.replace(`{{${index}}}`, value),
  messages[key],
);

test("a storage label joins the backend's data half to the translated half", () => {
  const english = translator(en);
  const chinese = translator(zhCN);

  const palbox = { storageKey: "world-container:1", label: "Alice", labelKey: "Editor_Container_Palbox", labelArgs: [] };
  assert.equal(formatStorageLabel(palbox, english), "Alice · Palbox");
  assert.equal(formatStorageLabel(palbox, chinese), "Alice · 帕鲁终端");

  assert.equal(
    formatStorageLabel(
      { storageKey: "world-container:2", label: null, labelKey: "Editor_Container_Base", labelArgs: [2] },
      chinese,
    ),
    "基地 2",
  );
  assert.equal(
    formatStorageLabel(
      { storageKey: "global-palbox", label: null, labelKey: "Editor_Container_GlobalPalbox", labelArgs: [] },
      chinese,
    ),
    "跨界帕鲁终端",
  );
  assert.equal(
    formatStorageLabel(
      { storageKey: "world-container:3", label: "Home", labelKey: null, labelArgs: [] },
      chinese,
    ),
    "Home",
  );
});

test("a Pal that is not in the slot it records for itself has no storage to name", () => {
  assert.equal(formatStorageLabel(null, translator(zhCN)), "位置异常");
});
