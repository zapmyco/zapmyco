import logging
import inspect
import json


class LogUtil:
    """日志工具类"""

    @staticmethod
    def get_logger(name=None):
        """获取日志记录器"""
        if name is None:
            # 自动获取调用者的模块名
            frame = inspect.currentframe().f_back
            name = frame.f_globals["__name__"]
        return logging.getLogger(name)

    @staticmethod
    def log_request(logger, request, level=logging.INFO):
        """记录请求日志"""
        try:
            # 提取请求信息
            request_info = {
                "method": getattr(request, "method", "UNKNOWN"),
                "path": getattr(request, "path", "UNKNOWN"),
                "query": getattr(request, "query_string", ""),
                "headers": dict(getattr(request, "headers", {})),
            }

            # 移除敏感信息
            if "headers" in request_info and "authorization" in request_info["headers"]:
                request_info["headers"]["authorization"] = "[REDACTED]"

            logger.log(level, f"Received request: {json.dumps(request_info)}")

        except Exception as e:
            logger.error(f"Error logging request: {str(e)}")

    @staticmethod
    def log_response(logger, response, level=logging.INFO):
        """记录响应日志"""
        try:
            # 提取响应信息
            response_info = {
                "status": getattr(response, "status_code", 0),
                "headers": dict(getattr(response, "headers", {})),
            }

            # 记录响应体 (可能需要限制大小)
            body = getattr(response, "body", None)
            if body and len(body) < 1024:  # 限制为1KB
                try:
                    response_info["body"] = json.loads(body)
                except:
                    response_info["body"] = str(body)

            logger.log(level, f"Sending response: {json.dumps(response_info)}")

        except Exception as e:
            logger.error(f"Error logging response: {str(e)}")

    @staticmethod
    def log_execution(logger, execution_data, result, level=logging.INFO):
        """记录执行日志"""
        try:
            # 构建执行日志
            log_data = {
                "execution": execution_data,
                "result": {
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                },
            }

            if not result.get("success", False):
                log_data["result"]["error"] = result.get("error", "Unknown error")

            logger.log(level, f"Execution result: {json.dumps(log_data)}")

        except Exception as e:
            logger.error(f"Error logging execution: {str(e)}")
