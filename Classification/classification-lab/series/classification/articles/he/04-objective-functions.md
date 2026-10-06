---
title: "מה המודל באמת ממזער"
description: "Log loss, ציון Brier, hinge, exponential ו-focal. מתאימים רגרסיה לוגיסטית ביד עד שהיא תואמת את הספרייה, מגלים למה הניסיון הראשון שלנו לא תאם, ורואים אילו הבדלים בין פונקציות מטרה שורדים אחרי ההתכנסות."
series: "classification"
lang: "he"
order: 4
date: 2026-09-30
updated: 2026-10-04
keywords: ["פונקציות הפסד", "log loss", "ציון brier", "ירידה במורד הגרדיינט", "משקלי מחלקות", "numpy"]
readingTime: "11 דקות קריאה"
figure: "loss-and-impurity.png"
---

מתאימים רגרסיה לוגיסטית ביד עם 1,500 צעדים של ירידה במורד הגרדיינט, ומשווים ל-scikit-learn על אותו מודל ואותם נתונים. ההסתברויות החזויות נבדלות בעד @@v:objectives_discrepancy.csv|fit=gradient descent, 1,500 steps (the chapter's version)|max_abs_prob_diff_vs_reference|.2f@@ עבור רשומה אחת. מי מהן טועה? אף אחת, בערך, ולגלות למה זו הדרך המהירה ביותר להבין מה `fit()` עושה.

<div class="callout">

**מטרה.** להבין מה מסווג ממזער, ואילו הבדלים בין פונקציות מטרה הם אמיתיים אחרי שכל אחת התכנסה.

**תוכנית עבודה.** לחשב שני הפסדים ביד. לכתוב רגרסיה לוגיסטית ב-NumPy, למדוד את הפער מהספרייה ולסגור אותו. להתאים שש פונקציות מטרה עד התכנסות עם אותו קנס חלש ולהשוות דירוגים, הסתברויות והחלטות. לסכם את פונקציות המטרה בטבלה אחת.

</div>

## שני הפסדים על ארבע רשומות

הפסד (loss) הופך כל זוג (חיזוי, תוצאה) לקנס, ו-`fit()` מוצא פרמטרים שמקטינים את הקנס הממוצע.

```python
import numpy as np

y_true = np.array([1, 1, 0, 0])
p = np.array([0.9, 0.2, 0.1, 0.6])
log_loss = -(y_true * np.log(p) + (1 - y_true) * np.log(1 - p))
brier = (p - y_true) ** 2
print("log loss per record:", log_loss.round(3))
print("Brier per record   :", brier.round(3))
for wrong in (0.6, 0.9, 0.99):
    print(f"true=0, predicted {wrong}: log loss {-np.log(1 - wrong):.2f}, Brier {wrong ** 2:.2f}")
```

```output
(filled in by the build)
```

אל תשוו את גדלי שתי העמודות, כי היחידות שונות. השוו את הצורות: log loss ממשיך לגדול כשחיזוי שגוי נעשה בטוח יותר (0.92, 2.30, 4.61), בעוד Brier נעצר ב-1. Log loss הוא מינוס לוג הנראות של מודל ברנולי, ולכן מזעור שלו הוא שיטת הנראות המרבית. שניהם *כללי ציון תקינים* (proper scoring rules): בתוחלת, ההסתברות האמיתית ממזערת אותם. זו תכונה של ההפסד, לא ערובה שמודל מוגמר, מוגבל ומוסדר מכויל (חלק 11).

## רגרסיה לוגיסטית ביד, ותעלומה

הגרדיינט של ה-log loss הממוצע הוא `Xᵀ(p − y) / n`, ולכן ירידה במורד הגרדיינט היא לולאה קצרה. מטריצת התכנון היא הקידוד המלא של one-hot ועוד חותך, על 80% משורות הפיתוח. ה-20% האחרים הם סט אימות פנימי; חלק ההשוואה לא נוגעים בו.

<details>
<summary>קוד ההגדרה</summary>

```python
import pandas as pd
from scipy.optimize import minimize
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
tr, va = train_test_split(dev, test_size=0.2, stratify=y[dev], random_state=42)
cat = [c for c in X.columns if X[c].dtype == object]
prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat), remainder=StandardScaler())
A = np.c_[np.ones(len(tr)), prep.fit_transform(X.iloc[tr])]          # intercept + features
B = np.c_[np.ones(len(va)), prep.transform(X.iloc[va])]
ytr, yva = y[tr], y[va]
sigmoid = lambda z: 1 / (1 + np.exp(-np.clip(z, -35, 35)))
```

</details>

```python
def grad(w):                                                         # gradient of the mean log loss
    return A.T @ (sigmoid(A @ w) - ytr) / len(ytr)

def descend(steps, lr=0.5):
    w = np.zeros(A.shape[1])
    for _ in range(steps):
        w -= lr * grad(w)
    return w

ref = LogisticRegression(penalty=None, max_iter=20000, tol=1e-10).fit(A[:, 1:], ytr)
p_ref = sigmoid(B @ np.r_[ref.intercept_, ref.coef_[0]])

print(f"design matrix: {A.shape[1]} columns, rank {np.linalg.matrix_rank(A)}")
for steps in (1500, 20000):
    w = descend(steps)
    print(f"{steps:>6} steps: largest gradient entry {np.abs(grad(w)).max():.1e}, "
          f"largest probability difference from scikit-learn {np.abs(sigmoid(B @ w) - p_ref).max():.3f}")
```

```output
(filled in by the build)
```

למטריצת התכנון יש **@@j:objectives_notes.json|rank_deficiency|d@@ עמודות יותר מהדרגה שלה**, כי עמודות ה-one-hot של כל משתנה מסתכמות בעמודת החותך. זה יכול להסביר *מקדמים* שונים, אבל לא *חיזויים* שונים לרשומות שנבנו באותה דרך. התצפית השנייה מסבירה: אחרי 1,500 צעדים הגרדיינט אינו אפס. ההתאמה לא התכנסה, ועוד צעדים מצמצמים את אי ההסכמה. הכיוון הקשה ביותר הוא רמה נדירה: `default = yes` מופיעה ב-3 מתוך 41,188 רשומות, כולן "לא", ולכן התאמה בלי קנס ממשיכה לדחוף את המקדם שלה למטה (בערך ‎-8 בפתרון הספרייה, בערך 0 אחרי 1,500 צעדים). אופטימייזר מסוג quasi-Newton מסיים את העבודה:

```python
def loss_and_grad(w):
    z = A @ w
    return np.mean(np.logaddexp(0, -(2 * ytr - 1) * z)), grad(w)

res = minimize(loss_and_grad, np.zeros(A.shape[1]), jac=True, method="L-BFGS-B",
               options={"maxiter": 5000, "ftol": 1e-14, "gtol": 1e-9})
print(f"L-BFGS: largest gradient entry {np.abs(grad(res.x)).max():.1e}, "
      f"largest probability difference from scikit-learn {np.abs(sigmoid(B @ res.x) - p_ref).max():.1e}")
```

```output
(filled in by the build)
```

התאמות שהתכנסו מסכימות עד בערך 1e-5, יהיה חוסר הדרגה אשר יהיה. המודל שכתבנו ביד היה בסדר; כלל העצירה שלנו לא. **בודקים את הגרדיינט, לא רק את ההפסד**: הפסד שהפסיק לזוז אינו הוכחה למינימום. זו גם הסיבה שרגרסיה לוגיסטית אמיתית משתמשת כברירת מחדל בקנס L2, שנותן לבעיה פתרון יחיד ויציב.

## שש פונקציות מטרה, כל אחת מותאמת עד התכנסות

כל פונקציית מטרה למטה מותאמת עם אותה שגרת L-BFGS, אותו קנס L2 חלש (כדי שלכל בעיה יהיה פתרון יחיד) וסובלנות גרדיינט, על אותן 26,360 רשומות אימון, ומדורגת על אותן 6,590 רשומות אימות. הפסדי hinge ו-exponential נותנים שולי החלטה (margins), ולכן עמודות ההסתברות שלהם באות מסיגמואיד בעל פרמטר אחד שמותאם לציוני האימון. ההתאמה ה"משוקללת" סופרת כל חיובי @@j:objectives_notes.json|weight_vs_intercept_shift.weight|.1f@@ פעמים, כמו ש-`class_weight="balanced"` עושה.

@@table:objectives_comparison.csv|cols=loss,validation_ap,spearman_with_log_loss_scores,top10pct_overlap_with_log_loss,mean_probability,records_flagged_at_0.5,records_flagged_at_break_even,contribution_at_break_even|fmt=validation_ap:.3f;spearman_with_log_loss_scores:.3f;top10pct_overlap_with_log_loss:.2f;mean_probability:.3f;records_flagged_at_0.5:d;records_flagged_at_break_even:d;contribution_at_break_even:d|rename=loss:הפסד,validation_ap:AP,spearman_with_log_loss_scores:הסכמת דירוג עם log loss,top10pct_overlap_with_log_loss:חפיפה ב-10% העליונים,mean_probability:הסתברות ממוצעת,records_flagged_at_0.5:סומנו ב-0.5,records_flagged_at_break_even:סומנו ב-1/8,contribution_at_break_even:תרומה ב-1/8@@

*@@j:objectives_notes.json|validation_prevalence|.1%@@ מרשומות האימות נרשמות. כל שש ההתאמות התכנסו (הערך הגדול ביותר בגרדיינט מתחת ל-2e-7). התרומה משתמשת ברשימת המחירים להמחשה והיא סימולציה רטרוספקטיבית.*

- **דירוג.** עבור המודל הלינארי הזה על התכונות האלה פונקציות המטרה מסדרות רשומות באופן דומה מאוד: AP בין @@v:objectives_comparison.csv|loss=brier (on sigmoid)|validation_ap|.3f@@ ל-@@v:objectives_comparison.csv|loss=exponential|validation_ap|.3f@@, והסכמת דירוג עם log loss של לפחות @@v:objectives_comparison.csv|loss=squared hinge|spearman_with_log_loss_scores|.2f@@. זו תצפית על הניסוי הזה: מחלקת השערות לינארית יכולה לייצר הרבה דירוגים, והפסד אחר יכול לבחור אחד אחר עם נתונים אחרים או יותר רעש.
- **הסתברויות.** ההתאמות המשוקללת וה-focal מדווחות הסתברות ממוצעת של @@v:objectives_comparison.csv|loss=weighted log|mean_probability|.2f@@ ו-@@v:objectives_comparison.csv|loss=focal|mean_probability|.2f@@ כש-@@j:objectives_notes.json|validation_prevalence|.1%@@ נרשמים. אמרו להן להתעניין יותר בחיוביים, והן מדווחות הסתברויות עבור העולם המשונה הזה: מדרגות טובות, אומדני הסתברות גרועים.
- **החלטות.** סף של 1/8 הגיוני רק להסתברויות. כשמפעילים אותו על שני הפלטים האלה הוא בוחר את כל 6,590 הרשומות, כלומר "מתקשרים לכולם" (תרומה @@v:objectives_comparison.csv|loss=weighted log|contribution_at_break_even|d@@). ההפסד שינה את מה שהמספרים *אומרים*, לא את הסדר.

האם שקלול שווה להזזת הסף? עבור מודל מוגדר נכון ובלי קנס, יכול להיות. עם קנס ומדגם סופי, לא בדיוק: ההסתברויות של המודל המשוקלל נבדלות מ"פתרון log loss ועוד לוג-המשקל על החותך" בעד @@j:objectives_notes.json|weight_vs_intercept_shift.max_abs_prob_diff_weighted_vs_shifted_intercept|.2f@@ עבור רשומה אחת (הסכמת דירוג @@j:objectives_notes.json|weight_vs_intercept_shift.spearman_weighted_vs_log|.3f@@). אם אתם צריכים הסתברויות, אמנו עם משקלים טבעיים ובחרו את הסף אחר כך. Brier על סיגמואיד אינו קמור, ולכן הטבלה שומרת את הטוב מבין שתי נקודות התחלה (אפס ופתרון log loss); שתיהן התכנסו.

## מפת החלטה לפונקציות המטרה הנפוצות

| הפסד | צורה (שולי החלטה *m* = y·f(x), כש-y ב-{-1, +1}, או הסתברות) | פלט | מודלים אופייניים | מתי להשתמש | תוויות רועשות | כיול | פשרה |
|---|---|---|---|---|---|---|---|
| Log loss | -[y log p + (1-y) log(1-p)] | הסתברות | רגרסיה לוגיסטית, boosting, רשתות עצביות | צריכים הסתברויות | טעויות בטוחות עולות בלי גבול | כלל תקין; המודל המותאם עדיין צריך בדיקה | חלק, קמור למודלים לינאריים |
| Brier | (p - y)² | הסתברות | כל מודל הסתברותי; וגם ציון | קנס חסום על הסתברויות | סובל יותר (חסום) | כלל תקין | גרדיינט חלש כשטועים בביטחון; לא קמור על סיגמואיד |
| Hinge / squared hinge | max(0, 1 - m) / הריבוע שלו | שולי החלטה | SVM לינארי וקרנלי | דירוג בשוליים רחבים | בינוני | צריך קנה מידה של Platt או איזוטוני | רק רשומות ליד הגבול חשובות |
| Exponential | exp(-m) | שולי החלטה | AdaBoost | boosting עם עדכוני משקל מדויקים | רגיש מאוד | לא הסתברות | מהיר, שביר עם רעש בתוויות |
| Focal / weighted | (1-p_t)^γ · log loss, או log loss משוקלל מחלקות | הסתברות ממושקלת מחדש | גילוי בנתונים לא מאוזנים, רשתות עצביות | חיוביים נדירים, דוגמאות קשות | תלוי ב-γ ובמשקלים | מעוות הסתברויות בכוונה | הדגשה טובה יותר, כיול גרוע יותר |

המפה מתארת התנהגות רגילה; מערך נתונים, קנס או אופטימייזר מסוימים יכולים להתנהג אחרת. לא כל מסווג ממזער הפסד באיטרציות: רגרסיה לוגיסטית ממזערת log loss מוסדר; SVM לינארי, hinge ועוד L2; עצים בוחרים פיצולים בחמדנות כדי להקטין אי-טהירות (impurity); boosting מוסיף עצים בכיוון שמקטין הפסד; Naive Bayes מעריך הסתברויות קודמות וצפיפויות בנראות מרבית תחת הנחת אי-תלות (ספירה, בלי איטרציות); k-NN שומר את הנתונים; רשת עצבית ממזערת log loss בשיטות גרדיינט סטוכסטיות לא קמורות.

## ניתוח ומסקנה: מה למדנו

- **בודקים התכנסות ישירות.** ההתאמה של 1,500 הצעדים השאירה גרדיינט של בערך @@v:objectives_discrepancy.csv|fit=gradient descent, 1,500 steps (the chapter's version)|grad_inf_norm|.0e@@ והסתברויות שסטו בעד @@v:objectives_discrepancy.csv|fit=gradient descent, 1,500 steps (the chapter's version)|max_abs_prob_diff_vs_reference|.2f@@. התאמות שהתכנסו מסכימות עד 1e-5.
- **חוסר דרגה משנה מקדמים, לא חיזויים**, אבל הופך התאמה בלי קנס לאיטית ושברירית, ולכן קנס קטן הוא ברירת המחדל.
- **פונקציות מטרה נבדלות יותר במה שהמספרים אומרים מאשר באיך שהן מסדרות רשומות** כאן. אל תכלילו את זה מעבר למודל הזה ולתכונות האלה.
- **מתאימים בין הסף לפלט.** כלל נקודת האיזון מיועד להסתברויות, והפסדים שמשוקללים מחדש לא מספקים אותן.

*לקריאה נוספת.* Gneiting ו-Raftery (2007), [Strictly proper scoring rules, prediction, and estimation](https://doi.org/10.1198/016214506000001437); Lin ואחרים (2017), [Focal loss for dense object detection](https://doi.org/10.1109/ICCV.2017.324).

[חלק 5](/he/series/classification/05-logistic-regression-naive-bayes/) משתמש בגרסאות הספרייה של המודלים האלה ולומד לקרוא מה מודל לינארי למד.
