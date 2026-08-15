import assert from "node:assert/strict";
import test from "node:test";

import { formatContainerLabel } from "../src/components/modules/pal-container-label.js";
import en from "../src/i18n/en.js";
import zhCN from "../src/i18n/zh-CN.js";

const translator = messages => (key, args = []) => args.reduce(
  (text, value, index) => text.replace(`{{${index}}}`, value),
  messages[key],
);

test("container labels use descriptor metadata and the active locale", () => {
  const english = translator(en);
  const chinese = translator(zhCN);

  assert.equal(
    formatContainerLabel({ ContainerKind: "base", BaseOrdinal: 2 }, english),
    "Base 2",
  );
  assert.equal(
    formatContainerLabel({ ContainerKind: "base", BaseOrdinal: 2 }, chinese),
    "基地 2",
  );
  assert.equal(
    formatContainerLabel({ ContainerKind: "base", BaseName: "Home" }, chinese),
    "Home",
  );
  assert.equal(
    formatContainerLabel({ ContainerKind: "party", OwnerName: "Alice" }, chinese),
    "Alice · 队伍",
  );
  assert.equal(
    formatContainerLabel({ ContainerKind: "storage", OwnerName: "Alice" }, english),
    "Alice · Palbox",
  );
  assert.equal(
    formatContainerLabel(
      { ContainerKind: "dps", OwnerName: "Alice", ContainerLabel: "Stale DPS" },
      chinese,
      () => "后端旧名称",
    ),
    "Alice · 帕鲁次元仓库",
  );
  assert.equal(
    formatContainerLabel(
      { ContainerKind: "global_palbox", ContainerLabel: "Stale GPS" },
      english,
      () => "Stale backend name",
    ),
    "Global Palbox",
  );
  assert.equal(
    formatContainerLabel({ ContainerKind: "special", Shared: true }, chinese),
    "观赏笼",
  );
  assert.equal(
    formatContainerLabel({ ContainerKind: "special", OwnerName: "Alice", Size: 12 }, english),
    "Alice · Special container (12 slots)",
  );
  assert.equal(
    formatContainerLabel({ ContainerKind: "unknown", Size: 10 }, chinese),
    "未知容器（10 格）",
  );
  assert.equal(
    formatContainerLabel({ ContainerKind: "anomaly" }, chinese),
    "位置异常",
  );
});

test("container labels retain the backend fallback for unsupported metadata", () => {
  assert.equal(
    formatContainerLabel(
      { ContainerKind: "future", ContainerLabel: "Future container" },
      translator(en),
    ),
    "Future container",
  );
});
