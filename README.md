# 视觉设计趋势助手

每周一北京时间上午9点左右，联网研究最近7天的视觉设计变化并推送企业微信群。GitHub定时任务可能延迟。

## 配置
在 Settings → Secrets and variables → Actions → New repository secret 添加：
- WECOM_WEBHOOK_URL：企业微信群机器人的完整Webhook地址。
- OPENAI_API_KEY：有可用额度的OpenAI API密钥。ChatGPT订阅不代替API额度。

可选 Repository variable OPENAI_MODEL，默认 gpt-4.1，需支持Responses API及web_search。

## 首次验证
Actions → Design trend brief → Run workflow，mode=test，仅测试群消息（不调用AI）。
群里收到测试消息后，mode=brief 生成并发送完整简报，会使用API额度。
mode=preview 生成简报并保存Artifact，不发送群消息。
定时执行使用完整简报模式。失败会在Actions中显示，不自动重试，避免重复推送。

## 范围
见 brief.md，可直接编辑筛选规则。发送前要求联网搜索成功、生成完成且有来源引用。长消息按UTF-8字节拆分。
仅发送简报与来源，不自动修改个人知识库。密钥仅从GitHub Secrets读取，不提交到仓库。
代码使用Python标准库。生成简报保留为Actions Artifact 30天；不写入公开仓库。
