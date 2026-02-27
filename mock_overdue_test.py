import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, roc_curve
import warnings
warnings.filterwarnings("ignore")

print("1. 正在生成 1000000 条模拟信贷数据...")
np.random.seed(42)
N = 1000000

# ----------------- 造数核心逻辑 -----------------
# 1. 生成基础特征（无害的随机数）
loan_amount = np.random.uniform(5000, 50000, N)
interest_rate = np.random.uniform(0.05, 0.24, N)
credit_score = np.random.normal(650, 50, N)
risk_level_num = np.random.randint(1, 6, N)
customer_type_num = np.random.randint(1, 4, N)
days_since_approval = np.random.randint(10, 365, N)
days_to_next_due = np.random.randint(1, 30, N)

# 2. 埋入强特征：历史最大逾期天数 (大部分人是0，20%的人有逾期记录)
max_overdue_days = np.where(np.random.rand(N) > 0.8, np.random.randint(1, 90, N), 0)

# 3. 制造上帝视角的“隐藏真实违约风险分”（用来强行拉高 KS 值）
# 逻辑：历史逾期天数越长、负债(利率)越高、信用分越低，违约概率越大
hidden_risk_score = (
    max_overdue_days * 0.1 +         # 绝对的强变量
    (interest_rate * 20) +           # 利率也是强关联
    risk_level_num * 1.0 - 
    (credit_score - 600) * 0.02 + 
    np.random.normal(0, 3, N)        # 加入随机噪音，防止模型拟合得太完美(KS过高)
)

# 4. 强制截断：取全盘风险最高的前 4% 的人作为“真实逾期坏人”(制造严重不平衡)
threshold = np.percentile(hidden_risk_score, 96)
is_overdue_30 = (hidden_risk_score >= threshold).astype(int)

# 构建 DataFrame
feature_cols = [
    'loan_amount', 'interest_rate', 'credit_score',
    'risk_level_num', 'customer_type_num',
    'days_since_approval', 'max_overdue_days', 'days_to_next_due'
]
df = pd.DataFrame(dict(zip(feature_cols, [loan_amount, interest_rate, credit_score, risk_level_num, customer_type_num, days_since_approval, max_overdue_days, days_to_next_due])))
df['is_overdue_30'] = is_overdue_30


# ----------------- 核心代码 -----------------
print("2. 划分数据集并设置不平衡权重...")
X = df[feature_cols]
y = df['is_overdue_30']

# 面试点 1：必须强调用了 stratify=y 分层采样
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 面试点 2：不平衡权重的计算
pos_rate = y_train.mean()
scale_pos_weight = (1 - pos_rate) / pos_rate
print(f"-> 训练集正样本(逾期)比例: {pos_rate:.2%} | 计算得出的权重 scale_pos_weight: {scale_pos_weight:.2f}")

train_data = lgb.Dataset(X_train, label=y_train)
val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

# 你简历上的那套参数
params = {
    'objective': 'binary',
    'metric': 'auc',
    'learning_rate': 0.05,
    'num_leaves': 32,
    'max_depth': 4,
    'scale_pos_weight': scale_pos_weight,  # 将惩罚权重传入模型
    'verbose': -1
}

print("3. 开始训练 LightGBM 模型...")
model = lgb.train(
    params,
    train_data,
    num_boost_round=150,
    valid_sets=[train_data, val_data],
    callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
)

print("\n================ 模型评估结果 ================")
# 获取验证集预测概率 (注意：LGBM的predict输出的就是概率)
y_prob = model.predict(X_val)

# 面试点 3：手撕 AUC 和 KS 的计算逻辑
auc_score = roc_auc_score(y_val, y_prob)
fpr, tpr, thresholds = roc_curve(y_val, y_prob)
ks_value = max(tpr - fpr)  # KS的核心数学定义：真正率和假正率的最大差值

print(f"模型 AUC:  {auc_score:.4f}")
print(f"模型 KS值: {ks_value:.4f}")


# 面试点 4：输出特征重要性 (业务解释)
print("\n================ 特征重要性排名前 5 ================")
# 取出特征重要性 (基于增益 Gain，这在风控里比按分裂次数 split 更能体现特征价值)
importance = model.feature_importance(importance_type='gain')
feature_imp = pd.DataFrame({'Feature': feature_cols, 'Importance': importance})
feature_imp = feature_imp.sort_values(by='Importance', ascending=False).reset_index(drop=True)

# 归一化打印出来好看一点
feature_imp['Importance(%)'] = (feature_imp['Importance'] / feature_imp['Importance'].sum()) * 100
for i, row in feature_imp.head(5).iterrows():
    print(f"Top {i+1}: {row['Feature']:<20} | 贡献占比: {row['Importance(%)']:.2f}%")