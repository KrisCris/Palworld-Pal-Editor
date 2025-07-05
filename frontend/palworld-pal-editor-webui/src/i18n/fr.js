import TopBar from "@/components/TopBar.vue";

export default {
    AuthView_PW_Prompt_1: "Bonjour ! Il semble que vous ayez défini un mot de passe de protection 🔐.",
    AuthView_PW_Prompt_2: "Avant de continuer, veuillez entrer le mot de passe :",
    AuthView_BTN_Unlock: "Déverrouiller",

    EntryView_Greet_1: "Bonjour !",
    EntryView_Greet_2: " > Merci d'utiliser cet outil !",
    EntryView_Greet_3:
        " > Si vous utilisez cet outil en mode webui, ou depuis un conteneur Docker, pensez à configurer un mot de passe pour empêcher tout accès à distance non autorisé.",
    EntryView_Greet_4: " > Le lien de téléchargement pour Pal Editor est :",
    EntryView_Greet_4_1: "ou",
    EntryView_Greet_5: " page.",
    EntryView_Greet_6: " > Si vous aimez cet outil, envisagez de me soutenir pour m’aider à continuer à le développer et à l’entretenir. Visitez mon",
    EntryView_Greet_7: " > Vous rencontrez un problème ? Rejoignez",
    EntryView_Greet_7_1: "ou visitez",
    EntryView_Greet_8: " > Ma chaîne BiliBili (chinois) :",
    EntryView_Note_1:
        " > Si vous utilisez ce programme pour la première fois, vous devrez entrer manuellement le chemin correct vers votre dossier de sauvegarde, c'est-à-dire le dossier parent de Level.sav.",
    EntryView_Note_2:
        " > Après un chargement réussi de la sauvegarde, le chemin sera stocké et automatiquement renseigné pour vous la prochaine fois.",
    EntryView_Note_3:
        " > Si vous utilisez un conteneur Docker, assurez-vous d'avoir correctement mappé le répertoire et configuré les permissions d'accès aux fichiers. Ensuite, il vous suffira d'entrer le chemin mappé.",
    EntryView_BTN_Path_Picker: "Sélectionner le chemin",
    EntryView_BTN_Load: "Charger la sauvegarde",
    EntryView_Period: ".",
    EntryView_Version_Warning: "Cette version n'a pas été construite par le pipeline CI/CD officiel. Veuillez faire preuve de prudence et vérifier la source.",

    Editor_Note_Ghost_Pal: "CE PAL EST PROBABLEMENT NON RÉFÉRENCÉ DANS LE JEU",
    Editor_Basic_Info: "INFOS DE BASE",
    Editor_Species: "Espèce : ",
    Editor_Nickname: "Surnom : ",
    Editor_Gender: "Genre : ",
    Editor_Variant: "Variante : ",
    Editor_Pal_ID: "ID de l'instance de Pal : ",
    Editor_Pal_Guild_ID: "ID de la guilde de Pal : ",
    Editor_Pal_Slot: "Emplacement du conteneur de Pal : ",
    Editor_Pal_Owner: "Propriétaire : ",
    Editor_Pal_No_Owner: "Aucun (TRAVAILLEUR DE BASE)",
    Editor_Estimated_HP: "PV max estimés : ",
    Editor_Estimated_ATK: "Attaque estimée : ",
    Editor_Estimated_DEF: "Défense estimée : ",
    Editor_Estimated_WorkSpeed: "Vitesse de fabrication estimée : ",
    Editor_IV: "IVs",
    Editor_IV_HP: "PV : ",
    Editor_IV_DEF: "DEF : ",
    Editor_IV_ATK: "ATQ : ",
    Editor_IV_MELEE: "CORPS À CORPS (Inutilisé) : ",
    Editor_Souls_Upgrade: "AMÉLIORATION DES ÂMES (Statue de Pouvoir)",
    Editor_Souls_HP: "PV : ",
    Editor_Souls_ATK: "Attaque : ",
    Editor_Souls_DEF: "Défense : ",
    Editor_Souls_CraftSpeed: "Vitesse de fabrication : ",
    Editor_Condenser: "AMÉLIORATION DU CONDENSEUR",
    Editor_Condenser_Rank: "Rang : ",
    Editor_Passive_Skills: "COMPÉTENCES PASSIVES",
    Editor_Select_Skill: "Ajouter des compétences",
    Editor_Equipped_Skills: "COMPÉTENCES ACTIVES ÉQUIPÉES",
    Editor_Skill_ATK: "Attaque : ",
    Editor_Skill_CD: "CD : ",
    Editor_Skill_EL: "Élément : ",
    Editor_Mastered_Skills: "COMPÉTENCES ACTIVES MAÎTRISÉES (LES COMPÉTENCES SONT AJOUTÉES AUTOMATIQUEMENT LORS DE LA MONTÉE EN NIVEAU DES PALS)",

    Editor_Suitabilities: "Capacités de travail",

    Editor_Btn_Export_Data: "Exporter les données",
    Editor_Btn_Dupe_Pal: "Dupliquer Pal",
    Editor_Btn_Delete_Pal: "Supprimer Pal",
    Editor_Btn_Retrieve_Pal: "Récupérer",
    Editor_Btn_Heal_Pal: "Soigner le travailleur malade",
    Editor_Btn_Revive_Pal: "Réanimer Pal",

    PalList_Text: "LISTE DES PALS",

    PlayerList_Text: "LISTE DES JOUEURS",
    PlayerList_Viewing_Cage: "Déverrouiller la cage d'observation pour le joueur sélectionné. Remarque : Une fois déverrouillée, vous pouvez la construire directement, mais elle n'apparaîtra pas dans le menu de déverrouillage des technologies.",

    PlayerList_Base_Pal: "Camp De Base",

    TopBar_Btn_Save: "ENREGISTRER LES MODIFICATIONS",
    TopBar_Btn_Reload: "Recharger la sauvegarde",
    TopBar_Btn_Main_Page: "Retour à la page principale",
    TopBar_Btn_HealAllPals: "Guérir tous les Pals",
    TopBar_Btn_Pal_OOB: "Afficher Pal hors boîte",
    TopBar_Btn_Pal_Ghost: "Basculer Pal fantôme",
    TopBar_Btn_Invalid_Options: "Masquer triche",
    TopBar_Btn_Invalid_Options_ADs: "[Ce message n’apparaîtra qu’une seule fois. Si vous souhaitez consulter le contenu à nouveau, vous pouvez y accéder depuis la page d’entrée.] Je ne souhaite pas restreindre des fonctionnalités derrière un mur de paiement, mais si cet outil vous plaît, envisagez de me soutenir pour m’aider à continuer à le développer et à l’entretenir. Plus d’informations sont disponibles dans la section sponsor du README sur GitHub.",
    TopBar_Btn_Donation: "Donation",


    TopBar_Btn_HealAllPals_Tooltips: "Supprime tous les états négatifs de Pal et rétablit la santé et la satiété.",
    TopBar_Pal_OOB_Tooltips: "Afficher les pals qui ne sont pas dans les conteneurs de pals du joueur propriétaire, c'est-à-dire la cage d'observation, ou pris par quelqu'un.",
    TopBar_Pal_Ghost_Tooltips: "Afficher les pals fantômes, ceux qui ne peuvent plus être trouvés dans le jeu, c'est-à-dire vendus, lâchés, abattus.",
    TopBar_Invalid_Options_Tooltips: "Masquez certaines options et menus déroulants qui ne sont normalement pas disponibles dans le jeu. Faites attention lors de leur utilisation.",

    Alert_Successful_Save: "Modifications enregistrées avec succès dans {{path}}.",
};