---
title: "בתוך המודל שנבחר: הסתמכות, קבוצות עמודות ואת מי הוא מחמיץ"
description: "חשיבות gain, חשיבות permutation, permutation מקובץ ואימון מחדש בלי קבוצה עונים על ארבע שאלות שונות. מפעילים את כל הארבעה על המודל שראיות הפיתוח היו בוחרות, ואז מסתכלים על טעויות תחת המדיניות הקפואה."
series: "classification"
lang: "he"
order: 15
date: 2026-09-30
updated: 2026-10-04
keywords: ["חשיבות תכונות", "permutation importance", "ablation", "ניתוח טעויות", "כיול לפי קטע", "lightgbm"]
readingTime: "14 דקות קריאה"
figure: "leaderboard-importance.png"
---

מערבבים יחד את חמש עמודות המקרו בנתוני ההשוואה, והדיוק הממוצע של המודל יורד ב-@@v:importance_groups.csv|group=macro (5 columns)|grouped_ap_drop_mean|.3f@@. מערבבים אותן אחת אחת, וחמש הירידות מסתכמות ב-@@v:importance_groups.csv|group=macro (5 columns)|sum_of_single_column_drops|.3f@@. מאמנים את המודל מחדש בלעדיהן והוא מפסיד רק @@v:importance_groups.csv|group=macro (5 columns)|ap_drop_vs_full|.3f@@. שלושה ניסויים, שלושה מספרים שונים, וכולם נכונים. הם עונים על שאלות שונות, והחלק הזה עוסק בהבחנה ביניהן.

<div class="callout">

**מטרה.** לתאר על מה מודל מותאם נשען, עם כלים שהמשמעות שלהם לא מתבלבלת, ולגלות איפה הוא טועה תחת המדיניות שבאמת היינו מפעילים.

**תוכנית עבודה.** לבחור את המודל שראיות הפיתוח היו בוחרות. להפעיל חשיבות gain, חשיבות permutation, permutation מקובץ ואימון מחדש בלי קבוצה. ואז לנתח את הטעויות של המדיניות הקפואה לפי קטע, עם גדלי הקבוצות והרווחים.

</div>

## איזה מודל, ואיך נבחר

המודל שנבדק הוא זה שקורא היה בוחר מראיות *הפיתוח*: ה-AP המוצלב הממוצע הגבוה ביותר בחיפוש של טבלת הדירוג, שהוא @@j:importance_notes.json|audited_model@@ (AP מוצלב @@j:importance_notes.json|cv_ap|.3f@@; AP בחלק ההשוואה @@j:importance_notes.json|comparison_ap|.3f@@). המדיניות שמשמשת לניתוח הטעויות היא הסף שלו מחוץ-לקיפול, @@j:importance_notes.json|threshold_oof|.3f@@, שנקבע לפני שחלק ההשוואה דורג. כל מה שכאן מתאר את המודל המותאם הזה על הנתונים האלה, עם התכונות האלה, לא boosting בכלל.

## ארבעה כלים, ארבע שאלות

| כלי | על איזו שאלה הוא עונה | מה הוא לא יכול לומר |
|---|---|---|
| חשיבות Gain | בכמה ההפסד באימון ירד בפיצולים על העמודה הזו? (שימוש בזמן האימון) | אם המודל *צריך* את העמודה על נתונים חדשים; הוא מעדיף עמודות עם הרבה פיצולים אפשריים |
| חשיבות Permutation | בכמה ה-AP של המודל המותאם הזה יורד כשערכי העמודה מעורבבים בין רשומות? (הסתמכות) | ערבוב יכול ליצור צירופים שלא קורים אף פעם, ועמודות מתואמות יכולות לחפות זו על זו |
| Permutation מקובץ | אותו דבר, עם ערבוב של כמה עמודות יחד כך שהקשרים ביניהן *בתוך* הקבוצה שורדים | הוא עדיין שובר את הקשרים בין הקבוצה לשאר העמודות, ולכן הירידה אינה חסם של שום דבר |
| אימון מחדש בלי קבוצה | כמה AP הולך לאיבוד כשמתאימים מחדש מודל עם אותן הגדרות בלי הקבוצה? (במה שאר העמודות יכולות להחליף) | ההגדרות לא כוונו מחדש, וזו חלוקה אחת עם כמה גרעיני התאמה |

אף אחד מהם אינו השפעה סיבתית. שום דבר כאן לא אומר ששינוי הכלכלה, הערוץ או החודש ישנה את ההחלטה של לקוח.

## במה המודל משתמש ועל מה הוא נשען

חשיבות permutation על חלק ההשוואה (10 ערבובים לכל עמודה), לצד חלקו של ה-gain באימון:

@@table:importance_permutation.csv|head=10|cols=feature,ap_drop_mean,ap_drop_sd|fmt=ap_drop_mean:.4f;ap_drop_sd:.4f|rename=feature:עמודה,ap_drop_mean:ירידת AP,ap_drop_sd:סטיית תקן בין ערבובים@@

@@table:importance_gain_lightgbm.csv|head=8|cols=feature,gain_share|fmt=gain_share:.1%|rename=feature:עמודה,gain_share:חלק מה-gain באימון@@

שני הדירוגים חופפים ונבדלים. `nr.employed` ו-`euribor3m` מובילות את שניהם, `pdays` חזקה הרבה יותר ב-permutation מאשר ב-gain, ול-`age` יש @@v:importance_gain_lightgbm.csv|feature=age|gain_share|.1%@@ מה-gain באימון (הרבה ספים מועמדים לעמודה רציפה) ובכל זאת ירידת ה-permutation שלה היא רק @@v:importance_permutation.csv|feature=age|ap_drop_mean|.4f@@. עמודה יכולה להיות בשימוש כבד באימון וכמעט לא להיות נשענים עליה בזמן החיזוי.

## קבוצות

לעמודות בקבוצה יש מידע חופף, ולכן מספרים של עמודה בודדת מעריכים אותן בחסר. שלושה דברים נמדדים לכל קבוצה: מערבבים את כל הקבוצה יחד, מערבבים את העמודות שלה בנפרד (סכום), ומאמנים מחדש בלעדיה. ה-AP אחרי האימון מחדש הוא ממוצע של שלושה גרעיני התאמה.

@@table:importance_groups.csv|cols=group,grouped_ap_drop_mean,sum_of_single_column_drops,retrained_ap_mean,retrained_ap_sd,ap_drop_vs_full|fmt=grouped_ap_drop_mean:.3f;sum_of_single_column_drops:.3f;retrained_ap_mean:.3f;retrained_ap_sd:.4f;ap_drop_vs_full:.3f|rename=group:קבוצה,grouped_ap_drop_mean:הקבוצה מעורבבת יחד,sum_of_single_column_drops:סכום ערבובים בודדים,retrained_ap_mean:AP אחרי אימון בלעדיה,retrained_ap_sd:סטיית תקן,ap_drop_vs_full:ירידה אחרי אימון מחדש@@

![שמאל: חשיבות permutation של עשר העמודות החשובות ביותר. ימין: שלוש מדידות לכל קבוצת עמודות.](/series/classification/figures/leaderboard-importance.png)
*איור 1. זהב: הקבוצה מעורבבת יחד. אפור: סכום ערבובים של עמודות בודדות. כחול כהה: ירידה אחרי אימון מחדש בלי הקבוצה.*

איך לקרוא את זה:

- **ערבוב קבוצה יחד גדול בהרבה מהסכום בעמודות המקרו** (@@v:importance_groups.csv|group=macro (5 columns)|grouped_ap_drop_mean|.3f@@ מול @@v:importance_groups.csv|group=macro (5 columns)|sum_of_single_column_drops|.3f@@). המודל מסתדר כשעמודה חופפת אחת מעורבלת אבל לא כשכולן. השורות המעורבבות יחד גם מצמידות ערכים כלכליים לרשומות שלא שייכים להן, ולכן זה מתאר הסתמכות על קלט מעוות, לא את המידע בעמודות, ו**אינו** חסם לכמה הן חשובות.
- **אימון מחדש אומר במה שאר העמודות יכולות להחליף.** בלי קבוצת המקרו אותן הגדרות מפסידות בערך @@v:importance_groups.csv|group=macro (5 columns)|ap_drop_vs_full|.3f@@ AP; בלי ההיסטוריה (`pdays`, `previous`, `poutcome`) @@v:importance_groups.csv|group=history (pdays, previous, poutcome)|ap_drop_vs_full|.3f@@; בלי עמודות לוח הזמנים @@v:importance_groups.csv|group=schedule (contact, month, day_of_week)|ap_drop_vs_full|.3f@@; ובלי שבע עמודות פרופיל הלקוח רק @@v:importance_groups.csv|group=customer profile (7 columns)|ap_drop_vs_full|.3f@@, בערך בגודל הפיזור בין גרעיני ההתאמה (@@v:importance_groups.csv|group=customer profile (7 columns)|retrained_ap_sd|.4f@@).
- **מה המספר האחרון אומר.** לתהליך ולחלוקה האלה עמודות הפרופיל מוסיפות מעט *כשהאחרות נמצאות*. זה לא הופך את המאפיינים של לקוחות ללא רלוונטיים או התאמה אישית לבלתי אפשרית; זה אומר ששבע העמודות האלה מוסיפות מעט מעבר להיסטוריה, ללוח הזמנים ולהקשר המקרו כאן.
- **עמודות המקרו אולי מחליפות את הזמן** (חלק 6 הראה ש-`nr.employed` עוקבת אחרי המיקום בקובץ). מודל שנשען עליהן חשוף לכל מה שמניע אותן. חלק 16 בודק כמה זה עולה.

## את מי המדיניות מחמיצה?

תחת המדיניות הקפואה (@@j:importance_notes.json|audited_model@@, סף @@j:importance_notes.json|threshold_oof|.3f@@) חלק ההשוואה נותן:

@@table:errors_policy_counts.csv|cols=policy,records_selected,true_positives,false_negatives,positives|fmt=records_selected:d;true_positives:d;false_negatives:d;positives:d|rename=policy:מדיניות,records_selected:רשומות שנבחרו,true_positives:חיוביים אמיתיים,false_negatives:שליליים שגויים,positives:חיוביים@@

כלומר **@@v:errors_policy_counts.csv|false_negatives|d@@ מתוך 928 המנויים הם שליליים שגויים (false negatives)**: חיוביים שהמדיניות לא בחרה. דרך נוספת לפלח את החיוביים היא לפי המקום שלהם בדירוג. שלוש קבוצות, כולן מדווחות:

@@table:errors_positive_rank_groups.csv|cols=positives_group,positives,share_of_positives|fmt=positives:d;share_of_positives:.1%|rename=positives_group:קבוצת מנויים,positives:חיוביים,share_of_positives:חלק@@

ספירת החמצות לפי הרכב מטעה, כי לקטע עם הרבה רשומות יש הרבה החמצות. שיעורים טובים יותר. לכל קטע, הנה **שיעור השליליים השגויים בין המנויים שלו עצמו**, עם מספר המנויים ורווח Wilson של 95%:

@@table:errors_segments.csv|where=column~contact;poutcome;month|cols=column,level,records,positives,observed_rate,false_negatives,false_negative_rate_among_positives,fn_rate_lo,fn_rate_hi|fmt=records:d;positives:d;false_negatives:d;observed_rate:.3f;false_negative_rate_among_positives:.3f;fn_rate_lo:.3f;fn_rate_hi:.3f|rename=column:עמודה,level:רמה,records:רשומות,positives:חיוביים,observed_rate:שיעור הרשמה,false_negatives:הוחמצו,false_negative_rate_among_positives:חלק המנויים שהוחמצו,fn_rate_lo:נמוך 95%,fn_rate_hi:גבוה 95%@@

המדיניות מחמיצה @@v:errors_segments.csv|column=contact|level=telephone|false_negative_rate_among_positives|.0%@@ מהמנויים שנוצר איתם קשר בקו קווי, @@v:errors_segments.csv|column=month|level=may|false_negative_rate_among_positives|.0%@@ ממי שבמאי ו-@@v:errors_segments.csv|column=month|level=jul|false_negative_rate_among_positives|.0%@@ ממי שביולי, לעומת @@v:errors_segments.csv|column=contact|level=cellular|false_negative_rate_among_positives|.0%@@ ביצירות קשר סלולריות, וכמעט אף אחד עם הצלחה קודמת (@@v:errors_segments.csv|column=poutcome|level=success|false_negatives|d@@ מתוך @@v:errors_segments.csv|column=poutcome|level=success|positives|d@@). מאי לבדו מחזיק @@v:errors_segments.csv|column=month|level=may|false_negatives|d@@ מתוך @@v:errors_policy_counts.csv|false_negatives|d@@ ההחמצות כי הוא החודש הגדול ביותר. אלה מתארים מה מדיניות מבוססת ציון עושה, לא טעות בלתי נמנעת: מנויים במאי נראים הרבה כמו הרבה מי שלא נרשם במאי, ולכן הציונים מדרגים אותם נמוך. אם מידע חדש היה מפריד אותם (היסטוריית ערוצים שנמדדה, רשומת קשר עשירה יותר) זו השערה לבדיקה, לא רווח מובטח.

## כיול לפי קטע, עם רווחים

בדיקה ברמת קבוצה: האם הציון הממוצע של קטע יושב בתוך רווח ה-95% של שיעור ההרשמה שנצפה בו? על פני 27 הקטעים ב-`errors_segments.csv` (ערוץ, תוצאה קודמת, חודש ועבודה), התשובה היא כן לכל אחד (העמודה `mean_score_inside_rate_interval`). התאמה לממוצע הקבוצה היא בדיקה חלשה, היא לא מבססת כיול *בתוך* קטע, ועם 27 רווחים לא מתוקנים היינו מצפים שאחד או שניים יחמיצו במקרה. לקטעים קטנים, כמו @@v:errors_segments.csv|column=job|level=unknown|records|d@@ הרשומות עם עבודה לא ידועה, יש רווחים רחבים מדי כדי לומר הרבה.

## ניתוח ומסקנה: מה למדנו

- **שומרים את ארבע שאלות החשיבות נפרדות.** שימוש באימון, הסתמכות של מודל מותאם, הסתמכות על קבוצה, וההפסד אחרי אימון מחדש הם מספרים שונים. קבוצת המקרו מראה את שלושת הפיזורים בבת אחת.
- **Permutation של עמודה בודדת מעריך בחסר קבוצות מקובצות, ו-permutation של קבוצה מעריך ביתר את התלות** כי הוא מזין את המודל בקלט לא ריאלי. משתמשים באימון מחדש כהשוואה, עם ההסתייגויות שלו.
- **מגבילים מסקנות לתהליך, לחלוקה ולתכונות.** ירידה קטנה בקבוצת הפרופיל היא הצהרה על המודל הזה עם החלופות האלה.
- **מתארים טעויות לפי שיעור וגם לפי ספירה.** המדיניות מחמיצה @@v:errors_policy_counts.csv|false_negatives|d@@ מתוך 928 מנויים, מרוכזים בקטעים (קו קווי, מאי, יולי) שבהם הציונים נמוכים. הקובץ לא יכול לומר לנו למה.

[חלק 16](/he/series/classification/16-when-time-breaks-the-model/) שואל מה קורה כשהמודל צריך לחזות רשומות שבאות אחרי אלה שעליהן אומן.
