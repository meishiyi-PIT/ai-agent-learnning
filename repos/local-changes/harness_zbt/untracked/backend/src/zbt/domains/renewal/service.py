from zbt.api.v1.renewal_advice import RenewalAdviceData, RenewalAdviceResponse, RenewalPolicyResponse, RenewalRecommendationResponse, RenewalResponseMeta
from zbt.core.errors import AppError
from zbt.domains.agent.service import AgentThreadService
from zbt.domains.enrollment.service import EnrollmentService
from zbt.domains.identity.models import H5User


class RenewalAdviceService:

    def __init__(
        self,
        thread_service: AgentThreadService,
        enrollment:EnrollmentService,
        request_id:str
        # 需要补充：enrollment 服务（预校验保单用）、知识服务（把切片 ID
        # 还原成文档信息）等依赖
    ) -> None:
        self.enrollment = enrollment
        self.thread_service = thread_service
        self.request_id = request_id

    def get_advice(
        self,
        user: H5User,
        *,
        policy_id: str,
        question: str,
        request_id:str,
    ) -> dict:
        # **需要补充的逻辑**：
        # 1. 先确定性校验保单：属于当前登录用户且保障中（用
        #    enrollment.list_policies(user) 匹配 policy_id，或新增按 ID 查询方法）；
        #    校验不过直接抛
        #    RENEWAL_POLICY_NOT_AVAILABLE（404），不启动 Agent
        policy_id_num = 0
        policy = None 
        for item in self.enrollment.list_policies(user).items:
            if(policy_id == item.policy_id):
                policy = item

        if policy is None:
            raise AppError(
                "RENEWAL_POLICY_NOT_AVAILABL",
                "该保单不属于当前用户",
                404,
            )
        
        # 2. 调用 thread_service.create_customer_thread(user, title="续保规划")
        #    创建会话，返回结构里 thread id 在 "id" 字段
        thread_id = self.thread_service.create_customer_thread(user,title="续保规划")
        # 3. 把保单 ID 和用户问题组装成任务消息（必须带上保单 ID，
        #    Agent 只能通过工具查保单，不能凭空知道用户选了哪张），
        #    调用 thread_service.send_customer_message(user, thread_id=..., text=...)
        
        messages = self.thread_service.send_customer_message(user,thread_id=thread_id,text=f"用户问题：{question},保单Id:{policy_id}")
        # 4. send_customer_message 返回结构里有 run_id、thread_id、assistant_message、
        #    invoked_tools、trace_id、trace_url；
        #    从 assistant_message["cards"] 里找 type 为 "renewal_advice" 的块
        renewal_advice_block = None
        for card in  messages.assistant_message['cards']:
            if card.type == 'renewal_advice':
                renewal_advice_block = card.type
        # 5. 没有找到结构化块时抛 RENEWAL_ADVICE_NOT_SUBMITTED（502）
        if renewal_advice_block is None:
            raise AppError(
                "RENEWAL_ADVICE_NOT_SUBMITTED",
                "没找到续保意见",
                404,
            )    
        # 6. 把 Block、保单信息、固定方案、运行记录、Trace 补全成对外响应数据；
        #    知识引用要从 cited_chunk_ids 还原成文档标题、版本、摘录（现有
        #    KnowledgeService 没有这个方法，需要新增一个，例如
        #    resolve_chunks(chunk_ids)：从 chunk_id 解析文档 ID → 取文档 →
        #    重新切分 → 按序号取对应段落）

        return RenewalAdviceResponse(
            success=True,
            data=RenewalAdviceData(
               run_id=messages.run_id,
               thread_id=thread_id,
               status="COMPLETED",
               policy=RenewalPolicyResponse(
                   policy_id=policy.policy_id,
                   policy_no=policy.policy_no,
                   product_name=policy.product_name,
                   plan_name=policy.plan_name,
                   coverage_end=policy.coverage_end
               ),
               # 不知道从哪里拿到这个结果
               recommendation=RenewalRecommendationResponse(
                   decision=,

               ),
               missing_information=,
               evidence=,
               invoked_tools=,
               trace_id=messages.trace_id,  
               trace_url=messages.trace_url  
            ),
            meta=RenewalResponseMeta(
                request_id,
                sever_time,
            ),
        )