---
title: "קו הבסיס שחייבים לנצח: רגרסיה לוגיסטית ו-Naive Bayes"
description: "תהליך בלי דליפת מידע, ההגדרה האחת שחשובה, ואיך קוראים מקדמים בלי לקרוא יותר מדי. לשני מדדי מקרו שמתואמים ב-0.97 יש יחסי סיכויים בשני צדי ה-1. נסביר למה, ואז נשווה בין שתי גרסאות של Naive Bayes."
series: "classification"
lang: "he"
order: 5
date: 2026-09-30
updated: 2026-10-04
keywords: ["רגרסיה לוגיסטית", "naive bayes", "קו בסיס", "יחס סיכויים", "רגולריזציה", "scikit-learn pipeline"]
readingTime: "12 דקות קריאה"
figure: "ch05-odds-ratios.png"
---

מתאימים רגרסיה לוגיסטית על הנתונים האלה ומסתכלים על שני מדדי המקרו `emp.var.rate` ו-`cons.price.idx`. יחסי הסיכויים שלהם, לכל סטיית תקן, הם @@v:linear_odds_ratios.csv|term=emp.var.rate|odds_ratio|.2f@@ ו-@@v:linear_odds_ratios.csv|term=cons.price.idx|odds_ratio|.2f@@: אחד חותך את הסיכויים להרשמה בכ-90%, והשני יותר משלש אותם. שתי העמודות מתואמות ב-0.78, וכל אחת מתואמת חזק עם שאר עמודות המקרו (ראו בהמשך). דפוס כזה צריך לגרום לכם להיזהר ממה שמקדם טוען.

<div class="callout">

**מטרה.** לבנות את המודל הרציני הפשוט ביותר, לוודא שאין בו דליפת מידע, לכוונן את הכפתור האחד שלו, וללמוד מה המקדמים שלו אומרים ומה לא.

**תוכנית עבודה.** לשים את העיבוד המקדים בתוך המודל. לסרוק את עוצמת הרגולריזציה בהצלבה על שורות הפיתוח. לקרוא את המקדמים כיחסי סיכויים מול ייחוס מוצהר. ואז להשוות מולם שתי גרסאות של Naive Bayes.

</div>

## עיבוד מקדים בתוך המודל

כל מה שמודל לומד על הנתונים חייב לבוא משורות האימון בלבד: רשימות קטגוריות, ממוצעי עמודות, סטיות תקן. הדרך הפשוטה ביותר להבטיח את זה היא לשים את העיבוד המקדים *בתוך* האומד, כך ש-`fit` לומד אותו ו-`predict` רק מפעיל אותו, וההצלבה מתאימה מחדש את כל השרשרת בכל קיפול.

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
Xd, yd = X.iloc[dev], y[dev]
cat = [c for c in X.columns if X[c].dtype == object]
cv = StratifiedKFold(5, shuffle=True, random_state=42)

def model(C):
    prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore"), cat), remainder=StandardScaler())
    return make_pipeline(prep, LogisticRegression(C=C, max_iter=5000))

for C in (0.001, 0.01, 0.1, 1, 10):
    s = cross_val_score(model(C), Xd, yd, scoring="average_precision", cv=cv)
    print(f"C={C:<6} cross-validated AP {s.mean():.3f} +- {s.std(ddof=1):.3f}")
```

```output
(filled in by the build)
```

`OneHotEncoder` יוצר עמודות 0/1 (קטגוריה שלא נראתה באימון הופכת לאפסים) ו-`StandardScaler` מביא עמודות מספריות לסקאלה משותפת, וזה חשוב לקנס. התאמת ה-scaler על *כל* שורות הפיתוח לפני ההצלבה, ולא בתוך כל קיפול, שינתה את ה-AP ב-@@v:linear_pipeline_isolation.csv|model=Logistic regression|difference|.4f@@ ברגרסיה לוגיסטית וב-@@v:linear_pipeline_isolation.csv|model=k-nearest neighbours (k=50)|difference|.4f@@ ב-k-NN: דליפה זניחה כאן. אנחנו שומרים על התהליך בכל זאת, כי ההרגל חינמי וההשפעה במקומות אחרים יכולה להיות גדולה.

## ההגדרה האחת שחשובה

רגרסיה לוגיסטית ממזערת log loss ועוד קנס פרופורציונלי לסכום ריבועי המקדמים. ב-scikit-learn העוצמה מוגדרת הפוך: **`C` הוא ההופכי של עוצמת הקנס**, ולכן `C` קטן פירושו רגולריזציה כבדה ומקדמים קטנים ויציבים.

הטבלה למעלה מראה **מישור** (plateau): מ-`C = 0.1` ומעלה הציונים הממוצעים (@@v:linear_c_sweep.csv|C=0.1|cv_ap_mean|.3f@@ עד @@v:linear_c_sweep.csv|C=10.0|cv_ap_mean|.3f@@) נבדלים בכ-0.001, הרבה פחות מהפיזור בין קיפולים של כ-0.014. קנסות כבדים פוגעים (`C = 0.001` מקבל @@v:linear_c_sweep.csv|C=0.001|cv_ap_mean|.3f@@). כשיש תיקו כזה, לבחור את ההגדרה המוסדרת יותר היא ברירת מחדל סבירה. טבלת הדירוג בחלק 12 מכווננת את `C` באותו פרוטוקול כמו כל מודל אחר.

## מה מקדם אומר, ומה לא

במודל הזה המקדם *w* של תכונה הוא השינוי ב**לוג-הסיכויים** להרשמה כשהתכונה משתנה ביחידה אחת, כשכל שאר התכונות קבועות. מעלים אותו בחזקת e ומקבלים **יחס סיכויים**: 2.0 פירושו שהסיכויים מוכפלים, 0.5 פירושו שהם מתחצים.

נקודה טכנית קודם. כשכל קטגוריה מקודדת one-hot ועוד חותך, העמודות של כל משתנה מסתכמות בקבוע, ולכן מקדמים של דמי בודדים אינם מזוהים (חלק 4 מדד את חוסר הדרגה); רק *הפרשים* בין רמות משמעותיים. לכן הטבלה משתמשת ברמת ייחוס אחת שהוסרה לכל משתנה, השכיחה ביותר (@@j:linear_notes.json|reference_levels.contact@@ ליצירות הקשר, `month = @@j:linear_notes.json|reference_levels.month@@`, וכן הלאה), כך שיחס סיכויים קטגוריאלי הוא יחס מול הייחוס הזה. עמודות מספריות הן לכל סטיית תקן, והרווחים באים מ-100 התאמות בוטסטראפ של שורות הפיתוח.

@@table:linear_odds_ratios.csv|where=term~emp.var.rate;cons.price.idx;cons.conf.idx;euribor3m;nr.employed|cols=term,odds_ratio,or_lo,or_hi|rename=term:עמודה,odds_ratio:יחס סיכויים,or_lo:2.5%,or_hi:97.5%@@

![יחסי סיכויים בסקאלה לוגריתמית עם רווחי בוטסטראפ, לעמודות המקרו, עמודות ההיסטוריה וההשפעות הקטגוריאליות הגדולות ביותר.](/series/classification/figures/ch05-odds-ratios.png)
*איור 1. יחסי סיכויים נבחרים עם 95% האמצעיים של 100 התאמות בוטסטראפ.*

כמה תצפיות. יצירת קשר בקו קווי (לעומת סלולרי), כישלון קודם ושיחה ביום שני מורידים כל אחד את הסיכויים, והרווחים צרים. מרץ, ספטמבר, אוקטובר ודצמבר מעלים אותם בחדות לעומת מאי, אם כי בחודשים האלה יש מעט רשומות. לפנסיונרים יש סיכויים גבוהים יותר מאשר לעובדים אדמיניסטרטיביים.

עכשיו עמודות המקרו. כך הן מתואמות:

@@table:linear_macro_correlation.csv|fmt=emp.var.rate:.2f;cons.price.idx:.2f;cons.conf.idx:.2f;euribor3m:.2f;nr.employed:.2f@@

`emp.var.rate`, `euribor3m` ו-`nr.employed` הן כמעט אותו משתנה (מתאמים 0.91 עד 0.97), ולכן המודל מחלק ביניהן קרדיט וה*שילוב* של המקדמים נושא את האות. "כשהאחרים קבועים" מתאר אז כלכלות שלא התקיימו אף פעם. הפרידו בין שלושה דברים: מקדם בודד יכול להיות **לא יציב** כשעמודות חופפות (אף שהרווחים כאן די צרים), הוא **קשר מותנה** בהינתן העמודות האחרות, והוא **לא השפעה סיבתית**. קראו עמודות מתואמות כקבוצה.

## Naive Bayes: אותם נתונים, הנחה אחרת

Naive Bayes מדגם כל תכונה בנפרד בתוך כל מחלקה ומכפיל את התוצאות כאילו התכונות בלתי תלויות בהינתן המחלקה. הפרמטרים שלו מוערכים בנראות מרבית, ובמודלים האלה זה אומר ספירה וממוצעים, בלי איטרציות. משווים שתי גרסאות, שתיהן מדורגות עם הסתברויות מחוץ-לקיפול על שורות הפיתוח, ואת הרגרסיה הלוגיסטית כייחוס.

@@table:linear_naive_bayes.csv|cols=model,average_precision,roc_auc,log_loss,ece_10_quantile,mean_score,share_above_0.9,share_below_0.1|rename=model:מודל,average_precision:AP,roc_auc:AUC,log_loss:log loss,ece_10_quantile:ECE,mean_score:p ממוצע,share_above_0.9:חלק מעל 0.9,share_below_0.1:חלק מתחת ל-0.1|fmt=share_above_0.9:.3f;share_below_0.1:.3f@@

חלקם של המנויים הוא @@j:data_profile.json|prevalence|.3f@@. Gaussian Naive Bayes על עמודות one-hot, הגרסה הרגילה במדריכים, מדרג גרוע יותר מרגרסיה לוגיסטית וההסתברויות שלו רחוקות מאוד: log loss של @@v:linear_naive_bayes.csv|model=Gaussian NB on one-hot columns|log_loss|.2f@@ מול @@v:linear_naive_bayes.csv|model=Logistic regression (C=0.1)|log_loss|.2f@@, עם @@v:linear_naive_bayes.csv|model=Gaussian NB on one-hot columns|share_above_0.9|.0%@@ מהרשומות מעל 0.9. גאוסיאנים על עמודות 0/1 מתאימים גרוע, ולכן זה קו בסיס פגום בכוונה, לא מה ש-Naive Bayes יכול לעשות. הגרסה הקטגוריאלית עם עשרה סלי כמותיות מדרגת טוב יותר (AP @@v:linear_naive_bayes.csv|model=Categorical NB on binned numerics|average_precision|.3f@@) אבל נשארת בטוחה מדי בעצמה: ראיות מתואמות (`emp.var.rate`, `euribor3m`, `nr.employed`) מוכפלות כאילו הן בלתי תלויות. דירוג ואיכות הסתברות הם כישורים נפרדים (חלק 11).

## ניתוח ומסקנה: מה למדנו

- **קו בסיס.** AP מוצלב של כ-0.45 עם רגרסיה לוגיסטית. מודלים מאוחרים צריכים לנצח אותו ביותר מהפיזור בין קיפולים.
- **כוונון.** ל-`C` יש מישור מ-0.1 ומעלה, ולכן בוחרים את ההגדרה המוסדרת יותר בין תיקו.
- **תהליכים.** העברת העיבוד המקדים לתוך המודל הסירה דליפה שהייתה זניחה כאן.
- **מקדמים.** הם קשרים מותנים ביחס לרמת ייחוס מוצהרת, ועמודות מתואמות צריך לקרוא יחד.
- **Naive Bayes.** האיכות שלו תלויה בייצוג. הגרסה של גאוסיאן על one-hot היא קו בסיס חלש, ושתי הגרסאות בטוחות מדי בעצמן כי הנחת האי-תלות סופרת פעמיים ראיות מתואמות.

[חלק 6](/he/series/classification/06-decision-trees/) שואל אם מודל שיכול למצוא אינטראקציות וספים מצליח יותר, ועד כמה קל לו להתאים את עצמו יותר מדי.
