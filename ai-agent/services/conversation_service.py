"""
对话服务 - MVP版本
"""
import uuid
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.conversation import (
    Conversation, Message, MessageRole, ConversationWithMessages,
    CreateConversationDTO, CreateMessageDTO
)
from app.models.context import ConversationContext

logger = structlog.get_logger()

class ConversationService:
    """对话服务 - 内存存储版本（MVP）"""
    
    def __init__(self):
        # 内存存储
        self.conversations: Dict[str, Conversation] = {}
        self.messages: Dict[str, List[Message]] = {}  # conversation_id -> messages
        self.contexts: Dict[str, ConversationContext] = {}  # conversation_id -> context
    
    async def create_conversation(self, dto: CreateConversationDTO) -> Conversation:
        """创建新会话"""
        try:
            # 生成会话ID
            conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
            
            # 创建会话对象
            conversation = Conversation(
                id=conversation_id,
                title=dto.title or "新的对话",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                message_count=0,
                metadata={}
            )
            
            # 存储会话
            self.conversations[conversation_id] = conversation
            self.messages[conversation_id] = []
            
            # 创建初始上下文
            self.contexts[conversation_id] = ConversationContext(
                conversation_id=conversation_id,
                recent_queries=[],
                search_history=[],
                mentioned_entities={},
                research_focus=None
            )
            
            # 如果有初始消息，添加它
            if dto.initial_message:
                await self.add_message(CreateMessageDTO(
                    conversation_id=conversation_id,
                    role=MessageRole.USER,
                    content=dto.initial_message
                ))
            
            logger.info(
                "Conversation created successfully",
                conversation_id=conversation_id,
                title=conversation.title
            )
            
            return conversation
            
        except Exception as e:
            logger.error("Failed to create conversation", error=str(e))
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取会话信息"""
        return self.conversations.get(conversation_id)
    
    async def get_conversation_with_messages(self, conversation_id: str) -> Optional[ConversationWithMessages]:
        """获取包含消息的完整会话"""
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return None
        
        messages = self.messages.get(conversation_id, [])
        
        return ConversationWithMessages(
            conversation=conversation,
            messages=messages
        )
    
    async def list_conversations(self, limit: int = 20, offset: int = 0) -> List[Conversation]:
        """获取会话列表"""
        conversations = list(self.conversations.values())
        # 按更新时间倒序排列
        conversations.sort(key=lambda x: x.updated_at, reverse=True)
        
        # 分页
        return conversations[offset:offset + limit]
    
    async def add_message(self, dto: CreateMessageDTO) -> Message:
        """添加消息"""
        try:
            # 检查会话是否存在
            conversation = self.conversations.get(dto.conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {dto.conversation_id} not found")
            
            # 生成消息ID
            message_id = f"msg_{uuid.uuid4().hex[:12]}"
            
            # 创建消息对象
            message = Message(
                id=message_id,
                conversation_id=dto.conversation_id,
                role=dto.role,
                content=dto.content,
                timestamp=datetime.now(),
                metadata={}
            )
            
            # 存储消息
            if dto.conversation_id not in self.messages:
                self.messages[dto.conversation_id] = []
            
            self.messages[dto.conversation_id].append(message)
            
            # 更新会话统计
            conversation.message_count += 1
            conversation.updated_at = datetime.now()
            
            # 更新会话标题（如果是第一条用户消息且没有自定义标题）
            if (dto.role == MessageRole.USER and 
                conversation.message_count == 1 and 
                conversation.title == "新的对话"):
                # 使用消息内容的前20个字符作为标题
                conversation.title = dto.content[:20] + ("..." if len(dto.content) > 20 else "")
            
            # 更新上下文
            await self._update_context(dto.conversation_id, message)
            
            logger.info(
                "Message added successfully",
                message_id=message_id,
                conversation_id=dto.conversation_id,
                role=dto.role.value
            )
            
            return message
            
        except Exception as e:
            logger.error("Failed to add message", error=str(e))
            raise
    
    async def get_messages(self, conversation_id: str, 
                          limit: int = 50, offset: int = 0) -> List[Message]:
        """获取会话消息"""
        messages = self.messages.get(conversation_id, [])
        # 按时间顺序返回
        return messages[offset:offset + limit]
    
    async def get_recent_messages(self, conversation_id: str, 
                                 count: int = 10) -> List[Message]:
        """获取最近的消息"""
        messages = self.messages.get(conversation_id, [])
        return messages[-count:] if messages else []
    
    async def get_conversation_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """获取会话上下文"""
        return self.contexts.get(conversation_id)
    
    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """更新会话标题"""
        try:
            conversation = self.conversations.get(conversation_id)
            if not conversation:
                return False
            
            conversation.title = title
            conversation.updated_at = datetime.now()
            
            logger.info(
                "Conversation title updated",
                conversation_id=conversation_id,
                new_title=title
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to update conversation title", error=str(e))
            return False
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        try:
            # 删除会话、消息和上下文
            deleted_conv = self.conversations.pop(conversation_id, None)
            deleted_msgs = self.messages.pop(conversation_id, None)
            deleted_ctx = self.contexts.pop(conversation_id, None)
            
            if deleted_conv:
                logger.info(
                    "Conversation deleted successfully",
                    conversation_id=conversation_id,
                    message_count=len(deleted_msgs) if deleted_msgs else 0
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to delete conversation", error=str(e))
            return False
    
    async def _update_context(self, conversation_id: str, message: Message):
        """更新会话上下文"""
        try:
            context = self.contexts.get(conversation_id)
            if not context:
                return
            
            # 如果是用户消息，更新查询历史
            if message.role == MessageRole.USER:
                # 添加到最近查询
                context.recent_queries.append(message.content)
                # 只保留最近10条查询
                if len(context.recent_queries) > 10:
                    context.recent_queries = context.recent_queries[-10:]
                
                # 简单的实体提取（关键词）
                content_lower = message.content.lower()
                
                # 检测论文相关关键词
                paper_keywords = ["论文", "paper", "文章", "研究", "study"]
                if any(keyword in content_lower for keyword in paper_keywords):
                    if "papers" not in context.mentioned_entities:
                        context.mentioned_entities["papers"] = []
                
                # 检测作者相关关键词
                author_keywords = ["作者", "author", "研究者", "学者"]
                if any(keyword in content_lower for keyword in author_keywords):
                    if "authors" not in context.mentioned_entities:
                        context.mentioned_entities["authors"] = []
                
                # 检测技术概念
                tech_concepts = ["transformer", "bert", "gpt", "attention", "深度学习", "机器学习"]
                for concept in tech_concepts:
                    if concept in content_lower:
                        if "concepts" not in context.mentioned_entities:
                            context.mentioned_entities["concepts"] = []
                        if concept not in context.mentioned_entities["concepts"]:
                            context.mentioned_entities["concepts"].append(concept)
            
        except Exception as e:
            logger.error("Failed to update context", error=str(e))
    
    async def get_conversation_history_for_llm(self, conversation_id: str, 
                                             max_messages: int = 10) -> List[Dict[str, str]]:
        """获取用于LLM的对话历史格式"""
        try:
            messages = await self.get_recent_messages(conversation_id, max_messages)
            
            # 转换为LLM格式
            llm_messages = []
            for message in messages:
                role = "user" if message.role == MessageRole.USER else "assistant"
                llm_messages.append({
                    "role": role,
                    "content": message.content
                })
            
            return llm_messages
            
        except Exception as e:
            logger.error("Failed to get conversation history for LLM", error=str(e))
            return []
    
    async def search_conversations(self, query: str, limit: int = 10) -> List[Conversation]:
        """搜索会话（简单文本匹配）"""
        try:
            results = []
            query_lower = query.lower()
            
            for conversation in self.conversations.values():
                # 搜索标题
                if query_lower in conversation.title.lower():
                    results.append(conversation)
                    continue
                
                # 搜索消息内容
                messages = self.messages.get(conversation.id, [])
                for message in messages:
                    if query_lower in message.content.lower():
                        results.append(conversation)
                        break
            
            # 按更新时间倒序排列
            results.sort(key=lambda x: x.updated_at, reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error("Failed to search conversations", error=str(e))
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            total_conversations = len(self.conversations)
            total_messages = sum(len(msgs) for msgs in self.messages.values())
            
            # 计算平均消息数
            avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
            
            # 最活跃的会话
            most_active = None
            max_messages = 0
            for conv_id, messages in self.messages.items():
                if len(messages) > max_messages:
                    max_messages = len(messages)
                    most_active = self.conversations.get(conv_id)
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "avg_messages_per_conversation": round(avg_messages, 2),
                "most_active_conversation": {
                    "id": most_active.id if most_active else None,
                    "title": most_active.title if most_active else None,
                    "message_count": max_messages
                } if most_active else None
            }
            
        except Exception as e:
            logger.error("Failed to get statistics", error=str(e))
            return {}
    
    async def cleanup_old_conversations(self, days: int = 30) -> int:
        """清理旧会话（MVP版本暂不实现自动清理）"""
        # MVP版本中暂时不实现自动清理功能
        logger.info("Cleanup not implemented in MVP version")
        return 0

# 全局对话服务实例
conversation_service = ConversationService()

