---
title: "שנים-עשר מודלים, פרוטוקול אחד: ראש בראש"
description: "שנים-עשר מסווגים וקו בסיס בלי מודל, מכווננים תחת פרוטוקול חיפוש אחד על נתוני הפיתוח ומדורגים פעם אחת על חלק ההשוואה. מה שווה, מה לא, ומה הטבלה יכולה ולא יכולה לומר."
series: "classification"
lang: "he"
order: 12
date: 2026-09-30
updated: 2026-10-04
keywords: ["השוואת מודלים", "benchmark", "xgboost", "lightgbm", "catboost", "יער אקראי", "רגרסיה לוגיסטית"]
readingTime: "12 דקות קריאה"
figure: "leaderboard-ap.png"
---

שישה מתוך שנים-עשר המודלים נוחתים בין @@v:leaderboard_selected.csv|model=XGBoost|cmp_average_precision|.3f@@ ל-@@v:leaderboard_selected.csv|model=sklearn HistGradientBoosting|cmp_average_precision|.3f@@ דיוק ממוצע על חלק ההשוואה, ורגרסיה לוגיסטית פשוטה יושבת על @@v:leaderboard_selected.csv|model=Logistic regression|cmp_average_precision|.3f@@. אם טבלת דירוג שימושית תלוי במה שמותר לה לטעון, ולכן החלק הזה מקדיש לפרוטוקול כמעט כמו לתוצאות.

<div class="callout">

**מטרה.** להשוות שנים-עשר מסווגים בהגינות תחת פרוטוקול מוצהר אחד, ולקרוא את התוצאה בלי לטעון יותר מדי.

**תוכנית עבודה.** לקבוע את השורות, התכונות והקיפולים, ולתת לכל מודל אותה שיטת חיפוש. להקפיא כל בחירה על נתוני הפיתוח, לדרג את חלק ההשוואה פעם אחת, ולדווח בנפרד על דירוג, הסתברויות, מהירות ורווח הכוונון. לסיים בטבלה של משפחות המודלים.

</div>

## הפרוטוקול

הכול נבחר על 32,950 רשומות הפיתוח ומדורג על 8,238 רשומות ההשוואה (928 מנויים). טיוטות מוקדמות של הסדרה כן הסתכלו על חלק ההשוואה תוך כדי חקירה, ולכן זה מדד הוראה מבוקר, לא סט מבחן חדש.

- **אותן רשומות, תכונות וקיפולים.** 18 התכונות הראשיות (חלק 2), החלוקה השכבתית (גרעין 42) והצלבה מעורבבת של 3 קיפולים לכל מודל.
- **אותה שיטת חיפוש, לא אותו חישוב.** כל מודל עם פרמטרים מעריך **8 מועמדים שונים**: ברירת המחדל של הספרייה ועוד שבע דגימות אקראיות ממרחב משלו, כל אחד מדורג לפי AP מוצלב ממוצע; הממוצע הטוב ביותר מנצח, ותיקו הולך לברירת המחדל. ברירת המחדל מדורגת גם על חלק ההשוואה כדי שאפשר יהיה לקרוא את השפעת הכוונון. הגדרות רציפות נדגמות מהתפלגויות רציפות, כך ששבע דגימות הן שבעה מועמדים שונים; הספירה נמדדת, ולקו בסיס בלי פרמטרים אין כזו. מספר מועמדים שווה אינו חישוב שווה, כיסוי שווה של כל מרחב, או הזדמנות שווה למודלים עם יותר הגדרות.
- **הייצוגים עוקבים אחרי כל משפחה:** עמודות one-hot ובקנה מידה לרגרסיה לוגיסטית, ל-SVM, ל-k-NN, לרשת העצבית ול-Naive Bayes; one-hot לעצים; קטגוריות טבעיות ל-XGBoost, ל-LightGBM ול-booster של scikit-learn; מחרוזות גולמיות ל-CatBoost, שמחשב סטטיסטיקות מטרה בעצמו. זה משווה *תהליכים שלמים*, לא אלגוריתמים מבודדים.
- **ה-boosters נעצרים באותה דרך:** 10% מנתוני האימון מוחזקים בצד, 30 סבבים בלי שיפור ב-log loss באימות, לכל היותר 2,000 עצים, חיזוי עם הסבב הטוב ביותר (ה-booster של scikit-learn עושה את זה פנימית). `n_estimators` לא נחפש.
- **שני מתאמים.** CatBoost צריך את שמות העמודות הקטגוריאליות בזמן ההתאמה, והעברתן ל-constructor גורמת ל-`sklearn.clone` לזרוק `RuntimeError` (נבדק עם ה-CatBoost המותקן), ולכן העטיפה מוצאת עמודות מחרוזת בעצמה. ה-SVM הלינארי יושב בתוך מכייל Platt שמכיל את העיבוד המקדים, עם קיפולים מעורבבים, כי קיפולים לא מעורבבים על קובץ מסודר בזמן הרסו את הדירוג שלו (חלק 9).
- **כניסות חלשות בכוונה או מוחרגות.** Gaussian Naive Bayes על עמודות one-hot הוא קו בסיס פגום (חלק 5); ה-SVM עם RBF מוחרג בגלל העלות שנמדדה (חלק 9). **שנים-עשר מודלים חזויים ועוד קו בסיס אחד בלי מודל מהווים שלוש-עשרה כניסות.**

## התוצאה

ממוין לפי AP בחלק ההשוואה. "CV AP" בחר את ההגדרה על נתוני הפיתוח; "default AP" היא ברירת המחדל של הספרייה שדורגה על חלק ההשוואה; קו הבסיס נותן לכל רשומה את השכיחות בפיתוח.

@@table:leaderboard_selected.csv|sort=cmp_average_precision|desc|cols=model,family,candidates_evaluated,selected,cv_ap,cmp_average_precision,cmp_ap_default,cmp_roc_auc,cmp_log_loss,cmp_ece_10_quantile|fmt=candidates_evaluated:d|rename=model:מודל,family:משפחה,candidates_evaluated:מועמדים,selected:נבחר,cv_ap:CV AP,cmp_average_precision:AP,cmp_ap_default:AP ברירת מחדל,cmp_roc_auc:AUC,cmp_log_loss:log loss,cmp_ece_10_quantile:ECE@@

![הדיוק הממוצע של כל מודל על חלק ההשוואה, עם רווחי בוטסטראפ של 95% למודל המותאם (אי-ודאות מדגם המבחן בלבד).](/series/classification/figures/leaderboard-ap.png)
*איור 1. הרווחים חופפים מאוד בששת העליונים.*

![עקומות ROC ודיוק-שלמות לחמישה מודלים.](/series/classification/figures/leaderboard-curves.png)
*איור 2. העקומות של המודלים החזקים קרובות. AP תלוי בחלקם של החיוביים (חלק 3).*

## מה הטבלה אומרת, ומה לא

- **קבוצה עליונה שהטבלה הזו לא יכולה לסדר.** XGBoost, CatBoost, extra trees, היער, LightGBM וה-booster של scikit-learn פרוסים על כ-0.013 AP, בעוד שלרווח של 95% ל-AP של מודל אחד יש רוחב של כ-0.07. חלק 13 מראה מה אפשר להפריד.
- **פער צנוע מקווי הבסיס הפשוטים.** רגרסיה לוגיסטית כ-0.03 מתחת לטוב ביותר, ועץ בודד מכוונן משתווה אליה (@@v:leaderboard_selected.csv|model=Decision tree|cmp_average_precision|.3f@@). הרשת העצבית וה-SVM יושבים קרוב אליה.
- **כוונון חשוב מאוד באופן שונה בין משפחות.**

@@table:leaderboard_selected.csv|where=model!=Prior (no model)|sort=cmp_average_precision|desc|cols=model,selected,cmp_average_precision,cmp_ap_default|rename=model:מודל,selected:נבחר,cmp_average_precision:AP מכוונן,cmp_ap_default:AP ברירת מחדל@@

  איפה שברירת המחדל רחוקה מהגיונית כאן (עץ שגדל עד הסוף, extra trees, k-NN עם k = 5, יער בברירת מחדל, Naive Bayes) כוונון מוסיף הרבה. בארבעת ה-boosters, ציונים מכווננים וציוני ברירת מחדל נבדלים בלא יותר מ-0.009 עם סימן משתנה (XGBoost ו-LightGBM מעט נמוכים, השניים האחרים מעט גבוהים), וזה בתוך הרעש של חלוקה אחת: "ברירות המחדל כבר היו קרובות למישור". זה גם מראה למה ברירת המחדל חייבת להיות במרוץ.
- **הכיול אינו אחיד.** ל-Naive Bayes יש ECE של @@v:leaderboard_selected.csv|model=Gaussian Naive Bayes|cmp_ece_10_quantile|.3f@@ ו-log loss של @@v:leaderboard_selected.csv|model=Gaussian Naive Bayes|cmp_log_loss|.2f@@ לעומת כ-0.27 לרוב המודלים (חלק 11).
- **בעיה אחת.** בערך 41,000 רשומות, 18 תכונות, אות חלש ותוצאה נדירה. בעיה אחרת יכולה לסדר את הטבלה מחדש.

## מהירות וגודל, נמדדים בנפרד

אלה באים מהרצה נפרדת על מכונה פנויה אחרת, עם ההגדרות שנבחרו: ההתאמה הסופית, כל חיפוש המועמדים (מהרצת הדירוג, שלא הייתה על מכונה פנויה, ולכן סדר גודל בלבד), ניקוד 8,238 רשומות ההשוואה בבת אחת כולל עיבוד מקדים, וניקוד רשומה אחת בכל פעם.

@@table:timing.csv|cols=model,fit_seconds_best,search_seconds_total,batch_records_per_second,single_record_ms_median|fmt=batch_records_per_second:,.0f;single_record_ms_median:.1f;fit_seconds_best:.1f;search_seconds_total:,.0f|rename=model:מודל,fit_seconds_best:התאמה סופית (שניות),search_seconds_total:חיפוש - זמן שעון (שניות),batch_records_per_second:רשומות לשנייה בקבוצה,single_record_ms_median:רשומה בודדת (מילישניות)@@

![זמן התאמה סופי ותפוקת קבוצה מול הדיוק הממוצע על חלק ההשוואה.](/series/classification/figures/leaderboard-cost-vs-quality.png)
*איור 3. איכות מול עלות במכונה הזו, בהגדרת התהליכונים ובגרסאות הספריות האלה (`timing_environment.json`).*

מודלים פשוטים הם המהירים ביותר להתאמה, ו-CatBoost האיטי ביותר לחיפוש בהגדרה הזו. השהיית רשומה בודדת נשלטת על ידי תקורת קריאה בתהליכי Python האלה, ולכן היא אומרת מעט על מערכת ייצור שנבנתה אחרת.

## המשפחות זו לצד זו

טבלה אחת לכל משפחה שבה משתמשים בסדרה הזו, עם הממצא של מערך הנתונים הזה אחרון. היא מסכמת התנהגות; היא לא דירוג אוניברסלי.

| משפחה (מודלים שנעשה בהם שימוש) | הנחה עיקרית | אינטראקציות | עמודות קטגוריאליות, קנה מידה | הסתברויות | קריא? | עלות | מתי להשתמש | כאן (AP) |
|---|---|---|---|---|---|---|---|---|
| לינארי: רגרסיה לוגיסטית, SVM לינארי | לוג-סיכויים (או שוליים) לינאריים בתכונות | רק אם מוסיפים | one-hot, קנה מידה | לוגיסטית: בדרך כלל סבירות; SVM: צריך כיול | גבוהה | נמוכה | קו בסיס מהיר שניתן להסבר | @@v:leaderboard_selected.csv|model=Logistic regression|cmp_average_precision|.3f@@ / @@v:leaderboard_selected.csv|model=Linear SVM (Platt scaled)|cmp_average_precision|.3f@@ |
| Naive Bayes (גאוסיאני) | תכונות בלתי תלויות בהינתן המחלקה | רק דרך הצפיפויות | one-hot, קנה מידה; הייצוג חשוב | בטוח מדי בעצמו (ראיות מתואמות נספרות פעמיים) | בינונית | נמוכה מאוד | בדיקת שפיות מהירה | @@v:leaderboard_selected.csv|model=Gaussian Naive Bayes|cmp_average_precision|.3f@@ |
| k שכנים קרובים | רשומות דומות, תוצאות דומות | דרך המרחק | one-hot, קנה מידה, k גדול | חלק השכנים | נמוכה | זול להתאמה, יקר לניקוד | נתונים קטנים, מבנה מקומי | @@v:leaderboard_selected.csv|model=k-nearest neighbours|cmp_average_precision|.3f@@ |
| SVM עם גרעין (RBF) | גבול חלק | כן | one-hot, קנה מידה | צריך כיול | נמוכה | עלות ההתאמה גדלה בחדות (חלק 9) | נתונים קטנים עד בינוניים | מוחרג (עלות) |
| רשת עצבית (MLP) | פונקציה חלקה | כן | one-hot, קנה מידה | מ-log loss; תלויה בגרעין | נמוכה | בינונית | נתונים גדולים, גרעינים חוזרים | @@v:leaderboard_selected.csv|model=Small neural net (MLP)|cmp_average_precision|.3f@@ |
| עץ החלטה | אזורים קבועים למקוטעין | כן, בחמדנות | one-hot; בלי קנה מידה | שיעורי עלים, גסים | גבוהה אם קטן | נמוכה | הסבר, כללים | @@v:leaderboard_selected.csv|model=Decision tree|cmp_average_precision|.3f@@ |
| Bagging: יער, extra trees | ממוצע מקטין שונות | כן | one-hot; בלי קנה מידה | תלויות בגודל העלה (חלק 11) | נמוכה | בינונית | ברירת מחדל חזקה וסלחנית | @@v:leaderboard_selected.csv|model=Random forest|cmp_average_precision|.3f@@ / @@v:leaderboard_selected.csv|model=Extra trees|cmp_average_precision|.3f@@ |
| Boosting: HistGradientBoosting, XGBoost, LightGBM, CatBoost | עצים קטנים מקטינים את הטעות שנותרה | כן | קטגוריות טבעיות בכמה ספריות; בלי קנה מידה | סבירות עם log loss; כדאי לבדוק | נמוכה | בינונית; עצירה מוקדמת | הנקודות האחרונות של איכות דירוג, עם משמעת אימות | @@v:leaderboard_selected.csv|model=XGBoost|cmp_average_precision|.3f@@ עד @@v:leaderboard_selected.csv|model=sklearn HistGradientBoosting|cmp_average_precision|.3f@@ |

בעיות רב-מחלקתיות ורב-תוויתיות מחוץ לסדרה הזו: כל מה שכאן הוא סיווג בינארי על טבלה.

## ניתוח ומסקנה: מה למדנו

- **מודלי boosting ו-bagging קיבלו את הציונים הגבוהים ביותר, קו בסיס פשוט צעד צנוע מתחתיהם, והסדר בתוך הקבוצה העליונה אינו מבוסס כאן.**
- **קו בסיס פשוט תחרותי משיקולים מעשיים:** מהיר, ניתן להסבר וקרוב בדירוג. אם הנקודות הנוספות מצדיקות את המורכבות זו שאלה לחלק 14.
- **ברירות מחדל הן חלק מההשוואה.** ל-boosters כוונון לא קנה שום דבר מדיד; לעצים, ליערות, ל-k-NN ול-Naive Bayes הוא קנה הרבה.
- **מספר מועמדים שווה הוא נוחות, לא הגינות.** התוצאות מתארות תהליכים שלמים עם המרחבים שכתבנו.

[חלק 13](/he/series/classification/13-is-the-winner-real/) שואל כמה מהסדר ישרוד מדגם אחר, חלוקה אחרת וחיפוש אחר.
