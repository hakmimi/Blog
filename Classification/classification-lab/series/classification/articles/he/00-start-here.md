---
title: "מתחילים כאן: הקדמה"
description: "איך הסדרה הזו בנויה, מה היא כוללת, מה התיאוריה הסטטיסטית שעומדת מאחורי מנגנון הקלסיפיקציה, איך הסיפור העסקי נכנס לתמונה, באילו נתונים ובאילו אלגוריתמים נשתמש ואיך נשווה ביניהם."
series: "classification"
lang: "he"
order: 0
label: "0"
date: 2026-10-04
updated: 2026-10-04
keywords: ["סיווג", "קלסיפיקציה", "למידת מכונה", "שיווק בנקאי", "מפת הסדרה", "פרוטוקול הערכה"]
readingTime: "10 דקות קריאה"
---
## מוטיבציה

כבר הרבה זמן חשבתי לכתוב סדרה על בעיות קלסיפיקציה, בעיות שבהן משתנה המטרה הוא משתנה בדיד וכולל שתי מחלקות או יותר (כן/לא, 1/0, א/ב/ג).

זה לא שאין חומרים טובים על בעיות קלסיפיקציה באינטרנט, פשוט לי תמיד היה חסר משהו. סוף סוף מצאתי את הזמן להכין את הסדרה הזו, וזה היה לפעמים מאתגר.

הרעיון פשוט: לעשות סדרה של פוסטים שמתמודדת עם בעיית קלסיפיקציה ספציפית מההתחלה ועד הסוף, כולל כל השלבים, ואפילו נותנת לה הקשר עסקי. לא עוד "נסווג מי ישרוד בטיטאניק", אלא בעיה אמיתית שהרבה ארגונים פיננסיים מתמודדים איתה בלייב.

לאורך העבודה השתדלתי לכסות צדדים שונים: יסודות תיאורטיים, היבטים עסקיים וכתיבת קוד. בחלקים המתקדמים יותר של הסדרה התייחסתי גם לסוגיות שפחות מצאתי עליהן חומר זמין, כמו מימד הזמן, אי-ודאות ומחיר כלכלי, כי לנושאים האלה יש משקל לא פחות חשוב והם נותנים תוקף אמיתי לכל עבודה.

הקוד נמצא במאגר ב-GitHub: [github.com/hakmimi/Blog](https://github.com/hakmimi/Blog) (הסקריפטים של הסדרה בתיקייה `series/classification/scripts`, וכל מספר בטקסט מודפס מהם).

אשמח לשמוע אם פספסתי או שגיתי לאורך הדרך. אני מקווה שמי שקורא את המאמרים ימצא בהם ערך אמיתי.

יצחק

## איך נראית בעיית קלסיפיקציה

לרשומה (למשל לקוח שעומד לקבל שיחה) יש מדידות $x = (x_1, \dots, x_d)$, ויש תוצאה אחת שמעניינת אותנו, $y \in \{0, 1\}$ (נרשם או לא נרשם). אנחנו מחפשים פונקציה שמקבלת את המדידות ומחזירה **ציון** $p(x)$ (הערכה להסתברות שהרשומה חיובית), ואז מקבלים **החלטה** $\hat y$ לפי סף $t$:

$$
x \;\longrightarrow\; p(x) \approx P(y = 1 \mid x) \;\longrightarrow\; \hat y = \begin{cases} 1 & p(x) \ge t \\ 0 & p(x) < t \end{cases}
$$

<div class="pipe" role="group" aria-label="מרשומה להחלטה">
<div><b>רשומה</b><span>מה ידוע לפני השיחה</span></div>
<div class="pipe-arrow" aria-hidden="true"></div>
<div><b>מודל</b><span>לומד מדוגמאות עבר</span></div>
<div class="pipe-arrow" aria-hidden="true"></div>
<div><b>ציון</b><span>p(x), בין 0 ל-1</span></div>
<div class="pipe-arrow" aria-hidden="true"></div>
<div><b>סף t</b><span>נגזר מהמחיר והערך</span></div>
<div class="pipe-arrow" aria-hidden="true"></div>
<div><b>החלטה</b><span>מתקשרים או לא</span></div>
</div>

הדבר החשוב לזכור מהשרטוט: **המודל רק נותן ציון. ההחלטה נולדת רק כשמוסיפים סף**, והסף נגזר מהעסק ולא מהסטטיסטיקה.

## הסיפור העסקי, הנתונים ומאיפה הם באים

מאחורי כל בעיית קלסיפיקציה עומד סיפור עסקי, והסיפור שלנו הוא על מוקד מכירות בבנק. כל שיחה עולה בזמן של נציג, ומספר השיחות ביום מוגבל. לכן השאלה האמיתית היא **למי להתקשר עכשיו**.

הנתונים הם *Bank Marketing* ממאגר [UCI Machine Learning Repository](https://doi.org/10.24432/C5K306), הקובץ `bank-additional-full.csv`, שפורסם על ידי Moro, Cortez ו-Rita. הם מתארים שיחות טלפון שיווקיות של בנק פורטוגזי שהציע פיקדון לזמן קצוב, בין מאי 2008 לנובמבר 2010. התיעוד אומר שהקובץ מסודר לפי תאריך, וחלק 16 נשען על כך.

יש בו @@j:data_profile.json|rows|d@@ שורות, 20 עמודות קלט ותוצאה אחת, `y`: האם הלקוח נרשם. @@j:data_profile.json|positives|d@@ שורות (@@j:data_profile.json|prevalence|.1%@@) אומרות כן. לנתונים יש רישיון משלהם (CC BY 4.0), ולכן הסדרה לא מפיצה אותם בעצמה. הסקריפט `download_data.py` מוריד את הקובץ ובודק את סכום הביקורת שלו. הנה כל הבדיקה בארבע שורות:

```python
import pandas as pd

df = pd.read_csv("bank-additional-full.csv", sep=";")
print(df.shape, "->", df["y"].eq("yes").mean().round(3), "share of yes")
print(df.columns.tolist()[:6], "...")
```

```output
(filled in by the build)
```

**הערה חשובה.** שורה היא *רשומה* (record), לא לקוח. בקובץ אין מזהה לקוח, ולכן אנחנו אף פעם לא טוענים שאנחנו יודעים כמה אנשים שונים הוא מכיל. חלק 1 מסביר למה.

**ההחלטה בשורה אחת.** אם שיחה עולה `c` והרשמה שווה `v`, כדאי להתקשר למישהו כשההסתברות שלו להירשם גבוהה מ-`c / v`. היחס הזה הוא *הסתברות האיזון*. המחירים בסדרה הם הנחות להמחשה, לא נתוני הבנק: @@j:protocol_manifest.json|price_list.cost_per_contact|.0f@@ לשיחה ו-@@j:protocol_manifest.json|price_list.value_per_subscription|.0f@@ להרשמה, כך שנקודת האיזון היא @@j:protocol_manifest.json|price_list.break_even_probability|.3f@@. **הציון מדרג אנשים, והמחירים קובעים איפה לעצור.**

## שפה משותפת: קצת סדר במונחים

- **מסווג (classifier).** פונקציה שמקבלת עובדות על רשומה ומחזירה *ציון* עבור המחלקה שמעניינת אותנו, כאן "יירשם".
- **הסתברות מול החלטה.**
  - ציון יכול להיות (או להיהפך ל) הסתברות.
  - *החלטה* היא מה שעושים איתו: מתקשרים או לא.
  - הגבול ביניהם הוא ה*סף* (threshold), ובחירתו היא החלטה עסקית.
- **חיובי ושלילי.** חיובי הוא המחלקה הנדירה שאנחנו מחפשים (1). שלילי הוא כל השאר (0).
- **שיעור בסיס (base rate).** חלקם של החיוביים בנתונים. כאן הוא בערך אחד מתוך תשעה, ולכן דיוק (accuracy) לבדו הוא שופט גרוע: מודל שתמיד עונה "לא" צודק ברוב המקרים ולא מוצא אף אחד.
- **אימון ומבחן.** דמיינו תלמיד שמתכונן למבחן. אם המבחן הוא בדיוק התרגילים שהוא כבר פתר, ציון גבוה רק מוכיח שהוא זוכר את התשובות. לכן מאמנים את המודל על חלק מהרשומות ובודקים אותו על רשומות שהוא מעולם לא ראה: כך מודדים הבנה ולא זיכרון.
- **דליפת מידע (leakage).** מצב שבו המודל "מציץ" בתשובה. למשל, אורך השיחה (`duration`) ידוע רק אחרי שהשיחה נגמרה, ושיחה ארוכה היא סימן שהלקוח התעניין. מודל שמשתמש בו נראה מצוין בטבלה, אבל ברגע ההחלטה, לפני שמרימים טלפון, המידע הזה לא קיים. חלק 2 מראה כמה זה משנה בקובץ הזה.
- **סחיפה (drift).** העולם משתנה. מודל שלמד מהעבר, כמו נהג שלמד לנהוג רק בקיץ, פוגש פתאום חורף: הלקוחות, התנאים והמחירים אחרים. חלק 16 מודד כמה זה עולה.

## מא' ועד ת': שלבי בניית מודל

כך בונים מודל קלסיפיקציה מההתחלה ועד הסוף. התרשים מראה את התהליך בחמש פאזות, ובכל שלב מצוין החלק בסדרה שעוסק בו. לחצו על שלב כדי לקפוץ אליו.

<div class="proc" role="group" aria-label="תרשים תהליך: אחד-עשר שלבים בחמש פאזות, עם לולאת חזרה">
<section class="proc-phase"><h4><span>א</span> הגדרה</h4><ol>
<li><a href="/he/series/classification/01-classification-is-a-decision/"><b>1</b><span>מגדירים את ההחלטה העסקית</span><small>מה מחליטים, ומה עולה כל טעות · חלק 1</small></a></li>
<li><a href="/he/series/classification/02-why-classification-is-hard/"><b>2</b><span>מבינים את הנתונים</span><small>רק מה שידוע ברגע ההחלטה · חלק 2</small></a></li>
</ol></section>
<div class="proc-arrow" aria-hidden="true"></div>
<section class="proc-phase"><h4><span>ב</span> הכנה</h4><ol>
<li><a href="/he/series/classification/03-what-does-good-performance-mean/"><b>3</b><span>קובעים איך מודדים הצלחה</span><small>דיוק, שלמות, AUC, AP · חלקים 3 ו-4</small></a></li>
<li><a href="#כללי-המשחק-מפה-פשוטה"><b>4</b><span>מפרידים נתונים</span><small>פיתוח, השוואה, זמן · המפה למטה</small></a></li>
</ol></section>
<div class="proc-arrow" aria-hidden="true"></div>
<section class="proc-phase"><h4><span>ג</span> בנייה</h4><ol>
<li><a href="/he/series/classification/05-logistic-regression-naive-bayes/"><b>5</b><span>בונים קו בסיס פשוט</span><small>מה שחייבים לנצח · חלק 5</small></a></li>
<li><a href="/he/series/classification/06-decision-trees/"><b>6</b><span>מנסים משפחות מודלים</span><small>עצים, יערות, boosting, רשתות · חלקים 6 עד 9</small></a></li>
<li><a href="/he/series/classification/10-hyperparameter-search/"><b>7</b><span>מכווננים בהגינות</span><small>אותו מאמץ לכל מודל · חלק 10</small></a></li>
</ol></section>
<div class="proc-arrow" aria-hidden="true"></div>
<section class="proc-phase"><h4><span>ד</span> החלטה</h4><ol>
<li><a href="/he/series/classification/11-probabilities-calibration-thresholds-costs/"><b>8</b><span>הופכים ציון להחלטה</span><small>כיול, סף, עלויות · חלקים 11 ו-14</small></a></li>
<li><a href="/he/series/classification/12-head-to-head-leaderboard/"><b>9</b><span>משווים ובודקים אם ההפרש אמיתי</span><small>אם לא, בוחרים את המודל הפשוט · חלקים 12 ו-13</small></a></li>
</ol></section>
<div class="proc-arrow" aria-hidden="true"></div>
<section class="proc-phase"><h4><span>ה</span> ביקורת והפעלה</h4><ol>
<li><a href="/he/series/classification/15-inside-the-winner/"><b>10</b><span>בודקים מבפנים ובזמן</span><small>על מה נשען, את מי מחמיץ · חלקים 15 ו-16</small></a></li>
<li><a href="/he/series/classification/16-when-time-breaks-the-model/"><b>11</b><span>מפעילים ומנטרים</span><small>סחיפה וחישוב מחדש · חלק 16</small></a></li>
</ol></section>
<div class="proc-loop"><b>↺ לולאת חזרה</b> אם הנתונים, המחירים או העולם משתנים, או שהבדיקה בשלב 10 מגלה בעיה, חוזרים לשלב 2 (מה מותר לקחת) או לשלב 4 (איך מפרידים) ובונים מחדש.</div></div>

*איור: תהליך בניית מודל מא' ועד ת'. התהליך אינו קו ישר: ממצא בשלב מאוחר מחזיר אותנו לשלבים מוקדמים.*

## כללי המשחק: מפה פשוטה

כדי שהשוואה בין מודלים תהיה הוגנת, כל המודלים בסדרה עוברים אותו מסלול. הנה המסלול על דף אחד (הגרסה המלאה בדף [השיטות](/he/series/classification/methods/)).

<div class="proto" role="group" aria-label="מפת הפרוטוקול: חלוקה לפיתוח והשוואה, והמבחן בזמן">
<div class="proto-row"><div class="proto-bar all"><b>כל הקובץ</b> @@j:data_profile.json|rows|d@@ רשומות</div></div>
<div class="proto-arrow" aria-hidden="true"></div>
<div class="proto-row"><div class="proto-bar dev" style="flex:80"><b>פיתוח · 80%</b><span>כאן מקבלים כל החלטה: בחירת הגדרות, ניסויים, כוונון בהצלבה (3 קיפולים). אותו מאמץ לכל מודל: ברירת מחדל ועוד עד שבעה מועמדים אקראיים.</span></div><div class="proto-bar cmp" style="flex:20"><b>השוואה · 20%</b><span>נוגעים פעם אחת, אחרי שהכול קפוא.</span></div></div>
<div class="proto-arrow" aria-hidden="true"></div>
<div class="proto-row"><div class="proto-bar out"><b>תוצאה</b> כמה מדדים, כל אחד עם אי-ודאות: דיוק ממוצע (AP), ROC-AUC, log loss, שגיאת כיול, ותרומה מדומה לפי רשימת המחירים</div></div>
<div class="proto-row sep"><div class="proto-bar time" style="flex:80"><b>הראשונים · 80% מהזמן</b><span>העבר: מאמנים ומכווננים כאן.</span></div><div class="proto-bar fut" style="flex:20"><b>האחרונים · 20%</b><span>העתיד: מדרגים כאן (חלק 16).</span></div></div>
</div>

*איור: למעלה, חלוקה אקראית (שכבתית, עם גרעין 42) לפיתוח ולהשוואה. למטה, מבחן נפרד לזמן: מאמנים על העבר ומדרגים על העתיד.*

ועוד שלושה כללים שאינם נראים בשרטוט:

- **רגע החיזוי הוא רגע לפני השיחה.** כל מה שידוע רק אחריה אינו קלט חוקי.
- **ההשוואה כבר נראתה בטיוטות מוקדמות.** לכן זה מדד הוראה מבוקר ולא סט מבחן שלא נגעו בו.
- **ההשוואה בין מודלים היא מזווגת.** משווים על אותן רשומות בדיוק, ומעריכים את אי-הוודאות בבוטסטראפ.

**מה המדד לא יכול להוכיח.** הוא לא יכול להראות שהתקשרות *גורמת* להרשמה. הוא לא יכול להראות שסדר השורות בקובץ הוא סדר לוח השנה האמיתי. והוא לא יכול להכתיר משפחת מודלים לכל טבלת נתונים, אלא רק לתאר איך שנים-עשר תהליכים קונקרטיים התנהגו על הנתונים האלה.

## איך שישה-עשר החלקים מתחברים

קוראים אותם כסיפור אחד בארבעה שלבים. לחצו על כל תיבה כדי לקפוץ לחלק.

<div class="flow" role="group" aria-label="תרשים זרימה של הסדרה: ארבעה שלבים, חלקים 1 עד 16">
<div class="flow-start"><a href="/he/series/classification/00b-from-lines-to-sigmoid/"><b>0 · 0b</b> מפה והכנה: קווים, סיגמואיד, תפוחים</a></div>
<div class="flow-arrow" aria-hidden="true"></div>
<section class="flow-stage"><h4><span>1</span> יסודות</h4><p>על מה אנחנו מחליטים, ואיך מדרגים?</p><ol>
<li><a href="/he/series/classification/01-classification-is-a-decision/"><b>1</b> ההחלטה</a></li>
<li><a href="/he/series/classification/02-why-classification-is-hard/"><b>2</b> הנתונים והמלכודות שלהם</a></li>
<li><a href="/he/series/classification/03-what-does-good-performance-mean/"><b>3</b> מה זה “טוב”</a></li>
<li><a href="/he/series/classification/04-objective-functions/"><b>4</b> מה המודל ממזער</a></li>
</ol></section>
<div class="flow-arrow" aria-hidden="true"></div>
<section class="flow-stage"><h4><span>2</span> מודלים</h4><p>איך כל משפחה עובדת, ועד כמה היא מצליחה?</p><ol>
<li><a href="/he/series/classification/05-logistic-regression-naive-bayes/"><b>5</b> רגרסיה לוגיסטית, Naive Bayes</a></li>
<li><a href="/he/series/classification/06-decision-trees/"><b>6</b> עצים</a></li>
<li><a href="/he/series/classification/07-bagging-random-forests/"><b>7</b> יערות</a></li>
<li><a href="/he/series/classification/08-gradient-boosting/"><b>8</b> Boosting</a></li>
<li><a href="/he/series/classification/09-other-classification-families/"><b>9</b> k-NN, SVM, רשת עצבית</a></li>
</ol></section>
<div class="flow-arrow" aria-hidden="true"></div>
<section class="flow-stage"><h4><span>3</span> כיול והחלטות</h4><p>איזה מודל מנצח, האם זה אמיתי, ומה זה שווה?</p><ol>
<li><a href="/he/series/classification/10-hyperparameter-search/"><b>10</b> כוונון בלי לרמות את עצמנו</a></li>
<li><a href="/he/series/classification/11-probabilities-calibration-thresholds-costs/"><b>11</b> הסתברויות, ספים, עלות</a></li>
<li><a href="/he/series/classification/12-head-to-head-leaderboard/"><b>12</b> ראש בראש</a></li>
<li><a href="/he/series/classification/13-is-the-winner-real/"><b>13</b> האם המנצח אמיתי?</a></li>
<li><a href="/he/series/classification/14-pricing-the-models/"><b>14</b> תמחור המודלים</a></li>
</ol></section>
<div class="flow-arrow" aria-hidden="true"></div>
<section class="flow-stage"><h4><span>4</span> ביקורת וזמן</h4><p>על מה המודל נשען, והאם הזמן שובר אותו?</p><ol>
<li><a href="/he/series/classification/15-inside-the-winner/"><b>15</b> בתוך המודל שנבחר</a></li>
<li><a href="/he/series/classification/16-when-time-breaks-the-model/"><b>16</b> כשהזמן שובר את המודל</a></li>
</ol></section>
<div class="flow-arrow" aria-hidden="true"></div>
<div class="flow-end"><b>התוצאה</b> דירוג, סף שנגזר מהמחירים, והצהרה מה אי אפשר להוכיח</div></div>

*איור 0. הסדרה כזרימה: כל שלב מעביר שאלה לשלב הבא.*

**יסודות (חלקים 1 עד 4).** *סיווג הוא החלטה* (1) מתחיל במודל שלא עושה כלום, צודק ב-88.7% מהמקרים ולא מוצא אף אחד. *למה הנתונים קשים* (2) בודק אילו עמודות מותר להשתמש בהן. *מה זה טוב* (3) מדרג מודל אחד בחמש דרכים. *מה המודל ממזער* (4) פותח את פונקציות המטרה.

**מודלים (חלקים 5 עד 9).** קו הבסיס שחייבים לנצח, רגרסיה לוגיסטית ו-Naive Bayes (5). אחר כך עצים (6), יערות (7), boosting (8), ומרחק, שוליים ורשתות (9). כל חלק מסביר איך המודל עובד, ואז מודד אותו.

**כיול והחלטות (חלקים 10 עד 14).** איך מכווננים בלי לרמות את עצמנו (10). האם ציונים הם הסתברויות (11). ראש בראש של כל שנים-עשר המודלים (12). האם המנצח אמיתי (13). כמה שווה הדירוג בכסף, לפי מחירים מוצהרים (14).

**ביקורת וזמן (חלקים 15 ו-16).** על מה המודל שנבחר נשען ואת מי הוא מחמיץ (15). ואז מה קורה כשהעתיד לא דומה לעבר (16).

עקיפה קצרה אחת עומדת לפני חלק 1. [חלק 0b](/he/series/classification/00b-from-lines-to-sigmoid/) מראה, עם 400 תפוחים מומצאים, למה קו ישר נכשל בשאלת כן/לא ולמה רשת של תאים מתאימה את עצמה יותר מדי לנתוני האימון (overfitting). זו התמונה הנקייה ביותר של הרעיון שעובר לאורך כל הסדרה.

המשיכו ל[חלק 0b](/he/series/classification/00b-from-lines-to-sigmoid/), או קפצו ישר ל[חלק 1](/he/series/classification/01-classification-is-a-decision/). ובינתיים, מעבדה קטנה לסיום.

## מעבדה חיה: איזה פרי זה?

זו ההדגמה הקטנה ביותר של כל מה שדיברנו עליו: מדידות נכנסות, מודל נותן ציון, וההחלטה היא המחלקה עם ההצבעה הגבוהה ביותר. הזיזו את המחוונים ושימו לב איך השכונה משתנה ואיך ההצבעה משתנה איתה. כאן המודל הוא k שכנים קרובים, שבו כל חיזוי ניתן לבדיקה: רואים בדיוק אילו דוגמאות תמכו בתשובה.

<div class="fruit-lab-widget" data-lang="he" data-src="/series/classification/artifacts/fruit_points.json"></div>
<script src="/js/fruit-lab.js"></script>

המעבדה המלאה, עם החישוב המתמטי, הקוד וההשוואה בין ארבעה מסווגים, נמצאת ב[עמוד המעבדה בעברית](/he/series/classification/fruit-lab/).
