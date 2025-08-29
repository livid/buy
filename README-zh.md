# buy-cli

一个简单的命令行工具，使用 Jupiter Swap API 在 Solana 上购买代币，代币铸造地址在 `config.py` 中配置。

- 输入 SOL 数量（第一个参数）
- 使用 Jupiter 官方 API (`/swap/v1/`) 创建交易并使用 `id.json` 密钥对签名

## 设置

- 确保 `config.py` 包含：
  - `mint`: 要购买的代币铸造地址
  - `rpc`: RPC 节点 URL
- 将 Solana 密钥对放在 `id.json` 中（64 或 32 个整数的数组）
- 可选：设置 `JUPITER_API_KEY` 环境变量以获得更高的速率限制

创建虚拟环境并安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## id.json 密钥对

`id.json` 文件包含 Solana 密钥对，应当极其小心地处理，因为它控制着钱包。

### 创建个性化地址

可以使用 `solana-keygen grind` 生成个性化地址（自定义前缀）的密钥对：

```bash
# 生成以 "Buy" 开头的地址的密钥对
solana-keygen grind --starts-with Buy:1 --ignore-case

# 生成以 "SOL" 结尾的地址的密钥对
solana-keygen grind --ends-with SOL:1 --ignore-case

# 生成特定前缀的密钥对（区分大小写）
solana-keygen grind --starts-with abcd:1
```

这将输出密钥对数组，可以将其保存到 `id.json`。

`solana-keygen` 可以通过以下方式安装：

```
brew install solana
```

### 保护密钥对

**重要提示**：始终使用适当的权限保护 `id.json` 文件：

```bash
# 设置仅所有者可读权限
chmod 600 id.json

# 验证权限
ls -la id.json
# 应显示：-rw------- 1 user group size date id.json
```

**安全最佳实践：**
- 永远不要分享 `id.json` 文件或将其提交到版本控制
- 将备份保存在安全的加密存储中
- 对于大额资金考虑使用硬件钱包
- 使用单独的密钥对进行测试/开发

## 使用方法

模拟运行（构建交易但不发送）：

```bash
python buy.py 0.005
```

广播（发送交易）：

```bash
python buy.py 0.005 --no-dry-run --yes
```

选项：
- `--slippage-bps` 默认 100 (1%)
- `--priority-fee` lamports 或 `auto`
- `--yes` 跳过确认
- `--no-dry-run` 进行广播

**API 信息：**
- 使用 Jupiter 官方 API (`lite-api.jup.ag/swap/v1/`)
- 支持付费计划的可选 API 密钥（设置 `JUPITER_API_KEY` 环境变量）
- 无需 API 密钥即可使用免费级别

## 使用 buy.sh 进行定期购买

对于自动化定期购买（定投），使用包含的 `buy.sh` 脚本：

```bash
# 确保它是可执行的
chmod +x buy.sh

# 运行定期购买
./buy.sh
```

该脚本将：
- 执行 30 次购买，每次 0.01 SOL
- 使用 25 个基点（0.25%）滑点
- 每次购买之间等待 5 分钟（300 秒）
- 自动确认每笔交易

### 自定义参数

编辑 `buy.sh` 以修改默认值：

```bash
ITERATIONS=30   # 购买次数
SIZE=0.01      # 每次购买的 SOL 数量
SLIPPAGE=25    # 滑点（基点）（25 = 0.25%）
SLEEP=300      # 购买之间的间隔秒数
```

**重要提示：**
- 确保有足够的 SOL 余额进行所有计划的购买
- 监控钱包余额和脚本的进度
- 考虑网络拥塞和交易费用
- 脚本运行期间如需停止请使用 `Ctrl+C`
