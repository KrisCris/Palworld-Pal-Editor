import assert from "node:assert/strict";
import test from "node:test";

import * as palEditor from "../src/stores/paleditor.js";

test("alpha Pals expose skins assigned to their base family", () => {
    const skins = [
        {
            SkinName: "Anubis_Skin001",
            TargetPalName: "Anubis",
            Invalid: false,
        },
        {
            SkinName: "PinkCat_Skin001",
            TargetPalName: "PinkCat",
            Invalid: false,
        },
    ];
    const selectedPal = {
        CharacterID: "Boss_Anubis",
        DataAccessKeyOG: "Boss_Anubis",
        FamilyID: "Anubis",
    };

    assert.deepEqual(
        palEditor.filterPalSkins?.(skins, selectedPal),
        [skins[0]],
    );
});

test("legacy Pal payloads match skins by their exact data key", () => {
    const skins = [{
        SkinName: "Anubis_Skin001",
        TargetPalName: "Anubis",
        Invalid: false,
    }];

    assert.deepEqual(
        palEditor.filterPalSkins?.(skins, { DataAccessKeyOG: "Anubis" }),
        skins,
    );
});

test("hidden invalid skins retain the skin currently applied to the Pal", () => {
    const current = {
        SkinName: "IceHorse_Skin001",
        TargetPalName: "IceHorse",
        Invalid: true,
    };
    const valid = {
        SkinName: "IceHorse_SkinValid",
        TargetPalName: "IceHorse",
        Invalid: false,
    };
    const hidden = {
        SkinName: "IceHorse_SkinUnused",
        TargetPalName: "IceHorse",
        Invalid: true,
    };

    assert.deepEqual(
        palEditor.filterPalSkins?.(
            [current, valid, hidden],
            {
                DataAccessKeyOG: "IceHorse",
                FamilyID: "IceHorse",
                SkinName: "IceHorse_Skin001",
            },
            true,
        ),
        [current, valid],
    );
});

test("showing invalid options reveals every skin for the selected family", () => {
    const skins = [
        {
            SkinName: "PinkCat_Skin001",
            TargetPalName: "PinkCat",
            Invalid: false,
        },
        {
            SkinName: "PinkCat_Skin002",
            TargetPalName: "PinkCat",
            Invalid: true,
        },
        {
            SkinName: "IceHorse_Skin001",
            TargetPalName: "IceHorse",
            Invalid: true,
        },
    ];

    assert.deepEqual(
        palEditor.filterPalSkins?.(
            skins,
            { FamilyID: "PinkCat", SkinName: null },
            false,
        ),
        skins.slice(0, 2),
    );
});
