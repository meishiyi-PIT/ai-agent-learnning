set -eu

# 从容器 secret 读取凭据，拒绝空内容；执行日志不输出密钥。
VLLM_API_KEY=$(cat /run/secrets/inference_api_key)
if [ -z "$VLLM_API_KEY" ]; then
    printf '%s\n' '生成服务密钥文件内容为空' >&2
    exit 1
fi
export VLLM_API_KEY

# 使用 exec 传递停止信号，vLLM 负责处理正在执行的请求。
exec python -m vllm.entrypoints.openai.api_server "$@"
