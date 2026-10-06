---
title: "למה הנתונים האלה קשים יותר ממה שנראה"
description: "עמודה אחת מעלה את הציון מ-0.45 ל-0.59 ואי אפשר להשתמש בה. אילו עמודות מותר להשתמש בהן, אילו לא ברורות, מה הקודים בקובץ אומרים, ולמה הנתונים משתנים עם הזמן."
series: "classification"
lang: "he"
order: 2
date: 2026-09-30
updated: 2026-10-04
keywords: ["דליפת מידע", "חוסר איזון בין מחלקות", "סחיפת התפלגות", "הנדסת תכונות", "pandas"]
readingTime: "10 דקות קריאה"
figure: "ch02-duration-leak.png"
---

מוסיפים עמודה אחת, `duration`, לרגרסיה לוגיסטית פשוטה, והדיוק הממוצע שלה (AP) קופץ מ-0.45 ל-0.59. זו הקפיצה הגדולה ביותר בכל הסדרה, והיא חסרת ערך. העמודה קיימת רק אחרי שהשיחה נגמרה.

במערכי נתונים אמיתיים יש הרבה עמודות כאלה, וגם קודים ומגמות שמטעים בשקט. החלק הזה בודק את הקובץ לפני שמאמינים לאיזשהו מודל.

<div class="callout">

**מטרה.** להחליט אילו עמודות מותר להשתמש בהן להחלטה "לדרג שיחות מתוכננות", ולהבין את הקודים ואת מבנה הזמן של השאר.

**תוכנית עבודה.** לשאול על כל עמודה מתי הערך שלה קיים. למדוד כמה שוות העמודות הלא ברורות. לבדוק את הקודים (`999`, `unknown`). ואז לראות איך שיעור ההרשמה זז לאורך הקובץ.

</div>

## המבחן שכל עמודה חייבת לעבור

על כל עמודה שואלים שאלה אחת: *ברגע שהבנק מחליט אם לבצע את השיחה הזו, האם הערך כבר קיים?* התיעוד של הקובץ (`bank-additional-names.txt`) אומר מה כל עמודה מתארת, וזה מספיק כדי למיין אותן.

| עמודה | קבוצה | תפקיד | זמינה | בסט הראשי |
|---|---|---|---|---|
| age | profile | customer | before | yes |
| job | profile | customer | before | yes |
| marital | profile | customer | before | yes |
| education | profile | customer | before | yes |
| default | profile | customer | before | yes |
| housing | profile | customer | before | yes |
| loan | profile | customer | before | yes |
| contact | schedule | policy | when scheduled | yes |
| month | schedule | policy | when scheduled | yes |
| day_of_week | schedule | policy | when scheduled | yes |
| duration | call outcome | outcome of the contact | after | no |
| campaign | contact count | policy | unclear | no |
| pdays | history | customer | before | yes |
| previous | history | customer | before | yes |
| poutcome | history | customer | before | yes |
| emp.var.rate | macro | context | before (as published) | yes |
| cons.price.idx | macro | context | before (as published) | yes |
| cons.conf.idx | macro | context | before (as published) | yes |
| euribor3m | macro | context | before (as published) | yes |
| nr.employed | macro | context | before (as published) | yes |

שלוש קבוצות עמודות דורשות הערה.

- **מדדי מקרו (macro indicators)** מתפרסמים רבעונית, חודשית או יומית. ערכים שפורסמו לפני השיחה הם קלט לגיטימי. בפריסה אמיתית, החלטה על שיחות *עתידיות* תצטרך לשים תחזיות או תרחישים במקומם, לא את הערכים שהתממשו ושמורים בקובץ הזה.
- **`contact`, `month`, `day_of_week`** מתועדות כתכונות של השיחה *האחרונה*. אנחנו מתייחסים אליהן כידועות ברגע שהשיחה נקבעת ביומן. זו הנחה, ולכן בהמשך יש הרצה אחת שמסירה אותן.
- **`campaign`** היא מספר השיחות בקמפיין, כולל האחרונה. נחזור אליה בהמשך.

## Duration: מספר השוואה שאי אפשר להשתמש בו

**מימוש.** מדרגים את אותו מודל על שורות הפיתוח עם `duration` ובלעדיה, בהצלבה של 5 קיפולים.

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)
dev, _ = train_test_split(np.arange(len(df)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)                      # development rows; the other 20% waits for part 12
cv = StratifiedKFold(5, shuffle=True, random_state=42)

def cv_ap(columns):
    cat = [c for c in columns if df[c].dtype == object]
    model = make_pipeline(make_column_transformer((OneHotEncoder(handle_unknown="ignore"), cat), remainder=StandardScaler()),
                          LogisticRegression(max_iter=2000))
    return cross_val_score(model, df.iloc[dev][columns], y.iloc[dev], cv=cv, scoring="average_precision").mean()

main = [c for c in df.columns if c not in ("duration", "campaign")]
print("main columns   :", round(cv_ap(main), 3))
print("main + duration:", round(cv_ap(main + ["duration"]), 3))
```

```output
main columns   : 0.448
main + duration: 0.589
```

**תוצאה.** על פני קבוצות התכונות שניסינו, עם רגרסיה לוגיסטית ומודל LightGBM בהגדרות ברירת המחדל של הספרייה (ממוצע דיוק ממוצע על 5 קיפולים; דירוג אקראי היה מקבל 0.113):

| קבוצת תכונות | Logistic regression | LightGBM |
|---|---|---|
| main | 0.448 | 0.463 |
| main + campaign | 0.449 | 0.465 |
| no schedule (profile, history, macro) | 0.423 | 0.444 |
| profile + history only | 0.338 | 0.344 |
| main + duration (not eligible; benchmark only) | 0.589 | 0.662 |

**מה זה אומר.** `duration` היא אורך השיחה האחרונה. התיעוד של הנתונים עצמו אומר שהיא "צריכה להיזרק אם רוצים מודל חיזוי ריאלי", והסיבה פשוטה: הערך לא קיים לפני השיחה. זה לבדו הופך אותה לבלתי שמישה להחלטה הזו, יהיה המנגנון מאחורי החוזק שלה אשר יהיה. להציג את הקפיצה כהצלחה של מודל זה להבטיח מודל שאי אפשר לבנות.

## Campaign: ספירה שקשורה למתי הבנק הפסיק

`campaign` סופרת את השיחות שנעשו, כולל האחרונה. שאר עמודות השיחה מתארות את השיחה האחרונה, ולכן הספירה עשויה לתעד גם *מתי הבנק הפסיק להתקשר*, וזה יכול להיות תלוי בתוצאה (אולי אחרי הרשמה, ואולי אחרי שהבנק ויתר; התיעוד לא אומר). כך שיעור ההרשמה יורד ככל שהספירה עולה:

| שיחות בקמפיין (8 = 8 ומעלה) | רשומות | שיעור הרשמה |
|---|---|---|
| 1 | 17,642 | 13.0% |
| 2 | 10,570 | 11.5% |
| 3 | 5,341 | 10.8% |
| 4 | 2,651 | 9.4% |
| 5 | 1,599 | 7.5% |
| 6 | 979 | 7.7% |
| 7 | 629 | 6.0% |
| 8 | 1,777 | 4.1% |

שיחות מאוחרות יותר אולי קשות יותר, או שספירות גבוהות מסמנות רשומות שבהן הבנק המשיך לנסות, או שניהם; הקובץ הזה לא יכול להפריד ביניהם, ולכן אנחנו לא נשענים על העמודה. ההשמטה שלה עולה מעט מאוד: סט התכונות הראשי מקבל 0.448 עם רגרסיה לוגיסטית, ו-0.449 כשמוסיפים את `campaign` (LightGBM: 0.463 ו-0.465). לכן **סט התכונות הראשי** בשאר הסדרה הוא 18 העמודות שמסומנות "yes" בטבלה למעלה.

הסרה של עמודות לוח הזמנים גם היא מורידה את הרגרסיה הלוגיסטית ל-0.423; אם הן לא ידועות בזמן קביעת השיחה, צפו לתוצאות קרובות יותר לשורה הזו.

## קודים שנראים כמו מספרים או כערכים

- **`pdays = 999`** פירושו "לא נוצר קשר קודם" (96.3% מהרשומות). זה מצב, לא מרחק של 999 ימים. מודל לינארי או מבוסס מרחק מתייחס אליו כאל מספר, ולכן השווינו את זה לייצוג שמפריד בין המצב לבין הזמן שעבר (דגל 0/1 ועוד הימים, כשהם מוגדרים 0 כשלא נוצר קשר):

| מודל | raw value (999 = never contacted) | flag + recency |
|---|---|---|
| Logistic regression | 0.448 | 0.447 |
| k-nearest neighbours | 0.320 | 0.316 |
| LightGBM | 0.463 | 0.462 |

  בנתונים האלה שני הייצוגים מקבלים אותו ציון בתוך הפיזור בין קיפולים. אנחנו משאירים את העמודה הגולמית בהשוואה הראשית, והקידוד מחדש זמין לכל מודל שצריך אותו.
- **`unknown`** היא תווית מתועדת לערכים חסרים ב-`job`, `marital`, `education`, `default`, `housing` ו-`loan`. החלקים נעים בין 0.2% ב-`marital` ל-20.9% ב-`default`. אנחנו משאירים אותה כרמה נפרדת ולא טוענים שום דבר על הסיבה שערך חסר. הסרת הרשומות האלה הייתה מוחקת 26% מהנתונים ומשנה מי נמצא במדגם.
- **כפילויות.** 12 שורות כפולות במדויק הן מעט מדי כדי שיהיה לזה משמעות כאן.

## הקובץ זז

הקובץ מסודר לפי תאריך, אבל אין בו עמודת תאריך, ולכן מיקום השורה משמש כתחליף לזמן. חותכים אותו לעשרה חלקים שווים של 4,119 רשומות ובודקים בכל חלק את שיעור ההרשמה ואת ריבית ה-Euribor לשלושה חודשים:

![עמודות: חלק הרשומות שהסתיימו בהרשמה, בכל חלק של 4,119 רשומות לפי סדר הקובץ. קו: ממוצע euribor3m באותם חלקים.](/series/classification/figures/ch02-drift.png)
*איור 1. שיעור ההרשמה מטפס מ-2.8% בחלק הראשון ל-46.0% בחלק האחרון, בעוד ריבית ה-Euribor יורדת מכ-4.9% ל-0.8%.*

זה מתאם בקובץ שמכיל מחזור כלכלי אחד. רשומות מאוחרות יותר עשויות להיות שונות בגלל הכלכלה, בגלל אילו לקוחות הבנק בחר לפנות אליהם, בגלל איך הקמפיין התנהל, או בגלל איך הרשומות נשמרו; הקובץ לא יכול להגיד מה. מבחינה מעשית, מודל שאומן על רשומות מוקדמות פוגש עולם אחר אחר כך, ולכן יש שתי שאלות: *איזה אלגוריתם לומד את הקשר הזה הכי טוב?* (חלוקה אקראית, חלקים 3 עד 15) ו*איך מודל יתנהג על רשומות מאוחרות?* (חלוקה כרונולוגית, חלק 16).

## ניתוח ומסקנה: מה למדנו

`duration` נכשלת במבחן הזכאות; `campaign` לא ברורה וההשמטה שלה עולה כ-0.002 AP; `999` ו-`unknown` הם מבנה, והייצוג כמעט לא מזיז את הציון כאן; ושיעור ההרשמה נסחף לאורך הקובץ בלי סיבה ידועה, ולכן מתכננים סביב זה.

| שאלה | החלטה בסדרה הזו |
|---|---|
| אילו עמודות זכאיות? | 18 העמודות של הסט הראשי. |
| ומה אם לוח הזמנים לא ידוע מראש? | הרצת רגישות: הציונים יורדים לשורת "no schedule". |
| איך מטפלים ב-`999` וב-`unknown`? | `pdays` גולמית ו-`unknown` כרמה נפרדת; דגל וזמן שעבר נבדקים בחלק הזה. |
| חלוקה אקראית או כרונולוגית? | אקראית להשוואת אלגוריתמים, כרונולוגית לשאלת הפריסה. |

[חלק 3](/he/series/classification/03-what-does-good-performance-mean/) פונה לשאלה שאנחנו כל הזמן דוחים: אם לא דיוק, איך מדרגים מסווג?
