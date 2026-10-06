---
title: "Bagging ויערות אקראיים: ממוצע שמרחיק את הרעש"
description: "כל עץ מתאים את עצמו יתר על המידה בדרך אחרת, ולכן הממוצע שלהם טוב מכל אחד מהם. בונים bagging ביד, מודדים עד כמה העצים מתואמים, ובודקים מה אקראיות, מספר העצים וציוני out-of-bag באמת עושים."
series: "classification"
lang: "he"
order: 7
date: 2026-09-30
updated: 2026-10-04
keywords: ["bagging", "יער אקראי", "extra trees", "out-of-bag", "הקטנת שונות"]
readingTime: "11 דקות קריאה"
figure: "ch07-bagging.png"
---

עץ קטן אחד מקבל דיוק ממוצע של בערך @@v:bagging_curve_summary.csv|trees=1|mean|.2f@@ על שורות שלא ראה. מחשבים ממוצע של 200 עצים, שאף אחד מהם לא טוב יותר מקודם, והציון הוא בערך @@v:bagging_curve_summary.csv|trees=200|mean|.2f@@. אף עץ בודד לא השתפר. הממוצע השתפר, כי הטעויות של העצים בלתי תלויות בחלקן ומתקזזות.

<div class="callout">

**מטרה.** להבין למה ממוצע של הרבה עצים לא יציבים עובד, מה גורם לו לעבוד טוב יותר, ומה יער עולה.

**תוכנית עבודה.** לבנות bagging מאפס ולדרג אותו על שורות אימות פנימיות כשמספר העצים גדל. למדוד עד כמה העצים מתואמים. להשוות יערות אקראיים ו-extra trees. לבדוק כמה עצים מספיקים, ומה ציון ה-out-of-bag מספר.

</div>

## Bagging מאפס

**Bagging** (bootstrap aggregating) נותן לכל עץ מדגם משלו של שורות האימון, שנדגם עם החזרה, ומחשב ממוצע של ההסתברויות שהם חוזים. מדגם בוטסטראפ מכיל בערך 63% מהשורות השונות, חלקן כמה פעמים. כל הניסויים בחלק הזה מותאמים על 75% משורות הפיתוח (שורות ה*התאמה*) ומדורגים על ה-25% האחרים (שורות ה*אימות*). חלק ההשוואה לא בשימוש.

**מימוש.** מתאימים 200 עצים, אחד לכל מדגם בוטסטראפ, ומדרגים את הממוצע של n הראשונים.

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
fit, val = train_test_split(dev, test_size=0.25, stratify=y[dev], random_state=42)

cat = [c for c in X.columns if X[c].dtype == object]
prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat), remainder="passthrough")
A, B = prep.fit_transform(X.iloc[fit]), prep.transform(X.iloc[val])
yf, yv = y[fit], y[val]

rng = np.random.default_rng(0)
votes = []
for i in range(200):
    rows = rng.integers(0, len(A), len(A))                          # a bootstrap sample
    tree = DecisionTreeClassifier(min_samples_leaf=20, random_state=i).fit(A[rows], yf[rows])
    votes.append(tree.predict_proba(B)[:, 1])
votes = np.array(votes)

for n in (1, 5, 25, 100, 200):
    print(f"average of {n:>3} trees: validation AP {average_precision_score(yv, votes[:n].mean(axis=0)):.3f}")
```

**תוצאה.** הקטע מריץ גרעין בוטסטראפ אחד. חזרנו על כל הניסוי עם חמישה גרעינים, ולכן הטבלה מראה כמה העקומה עצמה משתנה.

@@table:bagging_curve_summary.csv|cols=trees,mean,std,min,max|rename=trees:עצים בממוצע,mean:AP ממוצע,std:סטיית תקן,min:מינימום,max:מקסימום|fmt=trees:d@@

```output
(filled in by the build)
```

![דיוק ממוצע באימות של אנסמבל bagging כשמוסיפים עצים; הקו הוא הממוצע על פני חמישה גרעינים, והסרט הוא הטווח.](/series/classification/figures/ch07-bagging.png)
*איור 1. ממוצע עוזר מהר, ואז מתיישר.*

**מה זה אומר.** ממוצע מעלה את הציון מכ-@@v:bagging_curve_summary.csv|trees=1|mean|.2f@@ לעץ אחד לכ-@@v:bagging_curve_summary.csv|trees=200|mean|.2f@@ ל-200, ויותר ממחצית הרווח מגיעה בחמשת העצים הראשונים; מעבר ל-50 עצים הממוצע זז בפחות מ-0.001 לכל הכפלה. זו הקטנת שונות: רווח חד-פעמי שמתיישר, עם פיזור בין גרעינים שגם הוא מצטמצם (סטיית תקן @@v:bagging_curve_summary.csv|trees=5|std|.3f@@ ב-5 עצים, @@v:bagging_curve_summary.csv|trees=200|std|.3f@@ ב-200).

כל עץ מתאים את עצמו יתר על המידה בדרך אחרת, ולכן חלק מהטעות שלהם אקראי ומתקזז בממוצע, וכמה מתקזז תלוי עד כמה העצים **מתואמים** (עצים זהים לא היו מרוויחים כלום). המתאם הממוצע בין זוגות של ציוני עצים הוא @@j:bagging_oob.json|mean_pairwise_tree_correlation_by_seed.0|.2f@@ לגרעין הראשון ו-0.67 עד 0.68 על פני כל החמישה: גבוה, כי כל העצים מתחילים מאותן עמודות חזקות (`nr.employed`, `euribor3m`, `pdays`). יש מקום לעצים פחות מתואמים להצליח יותר.

## הרעיון של יער אקראי

**יער אקראי** (random forest) מוסיף ל-bagging מרכיב אחד: בכל פיצול שוקלים רק תת-קבוצה אקראית של התכונות (`max_features`). העצים נאלצים להשתמש בחומר שונה, וזה מוריד את המתאם ביניהם, במחיר שכל עץ חלש מעט יותר. **Extra trees** הולכים רחוק יותר ובוחרים גם את סף הפיצול באקראי. הנה הווריאנטים, כל אחד עם 300 עצים ועלה מינימלי של 10, בשלושה גרעיני התאמה:

@@table:bagging_forest_summary.csv|cols=model,val_ap_mean,val_ap_sd,fit_seconds_mean|rename=model:וריאנט,val_ap_mean:AP באימות,val_ap_sd:סטיית תקן בין גרעינים,fit_seconds_mean:שניות התאמה|fmt=fit_seconds_mean:.1f@@

`max_features = sqrt` (בערך 8 מתוך 62 עמודות one-hot בכל פיצול) נותן את הציון הטוב ביותר מבין מה שנוסה ואת ההתאמה הקצרה ביותר. שימוש בכל התכונות, שהוא bagging פשוט של עצים בעוצמה מלאה, נותן את ה-AP הנמוך ביותר ואת ההתאמה הארוכה ביותר. Extra trees נוחתים קרוב ליער. הזמנים האלה באים ממכונה משותפת ועסוקה, ולכן סמכו על הסדר ולא על השניות (בחלק 12 יש זמנים ממכונה פנויה). הסדר תלוי במערך הנתונים הזה: עם נתונים אחרים `max_features` גדול יותר יכול לנצח.

## כמה עצים?

קל להוסיף עצים, אבל האם יותר תמיד טוב יותר? דירגנו יערות של 10 עד 600 עצים עם חמישה גרעיני התאמה כל אחד:

@@table:bagging_n_estimators_summary.csv|cols=n_estimators,mean,std,min,max|rename=n_estimators:עצים,mean:AP ממוצע,std:סטיית תקן,min:מינימום,max:מקסימום|fmt=n_estimators:d@@

הציון עולה מ-@@v:bagging_n_estimators_summary.csv|n_estimators=10|mean|.3f@@ עם 10 עצים ל-@@v:bagging_n_estimators_summary.csv|n_estimators=300|mean|.3f@@ עם 300, ואז מפסיק לזוז (@@v:bagging_n_estimators_summary.csv|n_estimators=600|mean|.3f@@ ב-600). הרצה בודדת לא חייבת להשתפר עם כל עץ שמוסיפים, כי הפיזור בין גרעינים (כ-0.003 ליערות קטנים) גדול כמו הרווחים המאוחרים. התייחסו ל-`n_estimators` כאל הגדרת משאב ויציבות, לא כמימד כוונון: השתמשו בכמות עצים שמספיקה כדי שהתוצאות יפסיקו להשתנות עם הגרעין, וכווננו את `min_samples_leaf` ואת `max_features`.

## ציוני out-of-bag

כל מדגם בוטסטראפ משאיר בחוץ בערך 37% מהשורות, ולכן כל שורת אימון היא "out of bag" בערך לשליש מהעצים. ממוצע של החיזויים של אותם עצים בלבד לכל שורה נותן הערכה שלא צריכה נתוני אימות נפרדים.

```python
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(300, min_samples_leaf=10, max_features="sqrt", oob_score=True, n_jobs=4, random_state=0).fit(A, yf)
print(f"out-of-bag AP : {average_precision_score(yf, rf.oob_decision_function_[:, 1]):.3f}")
print(f"validation AP : {average_precision_score(yv, rf.predict_proba(B)[:, 1]):.3f}")
```

```output
(filled in by the build)
```

ציון ה-out-of-bag נמוך מעט מציון האימות. הסבר מפתה אחד הוא שחיזויי out-of-bag משתמשים רק בכשליש מהעצים. בדקנו אותו: תת-קבוצות אקראיות של 100 מתוך 300 העצים נותנות AP באימות של @@j:bagging_oob.json|val_ap_random_100_of_300_mean|.3f@@ (סטיית תקן @@j:bagging_oob.json|val_ap_random_100_of_300_sd|.3f@@ על 20 דגימות), כמעט כמו כל ה-300 (@@j:bagging_oob.json|val_ap_300_trees|.3f@@), ולכן זה לא מסביר את הפער. הסברים אחרים לא בדקנו. הערכת out-of-bag גם מניחה שהרשומות ניתנות להחלפה ולא אומרת כלום על רשומות מאוחרות כשלנתונים יש מבנה של זמן (חלק 16).

## מה יער עולה

- **הטיה.** ממוצע מקטין שונות, אבל כל עץ עדיין חלק חמדני ורדוד למדי. Boosting (חלק 8) מתקן טעויות במקום לעשות להן ממוצע.
- **הסתברויות.** שיעורי עלים ממוצעים יכולים להיות דחוסים או פרושים יותר מדי, תלוי בגודל העלה. חלק 11 מודד את זה לברירת המחדל (עלה מינימלי 1) ולעלה של 10.
- **גודל ועלות חיזוי.** 300 עצים עם אלפי עלים פירושם קובץ מודל גדול יותר וניקוד איטי יותר ממודל לינארי. חלק 12 מדווח על זמנים שנמדדו.
- **פרשנות.** אי אפשר לקרוא 300 עצים. יש ציוני חשיבות, עם הסתייגויות (חלק 15).

## ניתוח ומסקנה: מה למדנו

- **יער הוא מכונה להקטנת שונות.** ממוצע העלה את ה-AP באימות מכ-@@v:bagging_curve_summary.csv|trees=1|mean|.2f@@ (עץ אחד) לכ-@@v:bagging_n_estimators_summary.csv|n_estimators=300|mean|.2f@@ (יער של 300 עם תת-קבוצות אקראיות של תכונות), כשרוב הרווח בעצים הראשונים.
- **הורדת המתאם בין עצים עוזרת בנתונים האלה.** תת-קבוצות אקראיות של תכונות קיבלו @@v:bagging_forest_summary.csv|model=RF max_features=sqrt|val_ap_mean|.3f@@ לעומת @@v:bagging_forest_summary.csv|model=RF max_features=1.0 (bagging)|val_ap_mean|.3f@@ ל-bagging פשוט עם אותו גודל עלה.
- **התייחסו למספר העצים כאל משאב.** הוא מייצב תוצאות; ההגדרות ששווה לכוונן הן גודל העלה וחלק התכונות.
- **בדקו ציון out-of-bag מול סט אימות אמיתי לפני שסומכים עליו**, ולעולם לא כראיה לגבי תקופות עתידיות.

*לקריאה נוספת.* Breiman (1996), [Bagging predictors](https://doi.org/10.1007/BF00058655); Breiman (2001), [Random forests](https://doi.org/10.1023/A:1010933404324).

[חלק 8](/he/series/classification/08-gradient-boosting/) תוקף את הצד השני של הבעיה: במקום ממוצע של עצים בלתי תלויים, כל עץ חדש לומד מהטעויות של אלה שלפניו.
