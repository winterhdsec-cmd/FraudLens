#!/usr/bin/env python3
"""
AI 反诈团伙画像系统 - 简化版后端服务
用于解决依赖问题，提供模拟数据
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import uuid
import time

# 初始化Flask应用
app = Flask(__name__)
CORS(app, origins=['http://localhost:5173'])

# 模拟数据
def get_mock_response():
    return {
        "success": True,
        "total_cases": 3,
        "triage_status": "success",
        "has_errors": False,
        "cases": [
            {
                "case_id": "CASE_001",
                "message_count": 15,
                "time_range": "0 - 14",
                "risk_level": "HIGH",
                "risk_label": "高风险",
                "risk_type": "danger",
                "risk_score": 95,
                "scam_type": "冒充客服",
                "victim": "张三",
                "amount": "¥50,000",
                "ai_report": "经分析，该案件为典型的冒充客服诈骗...",
                "keywords": ["客服", "退款", "验证码"],
                "steps": ["收到冒充客服电话", "诱导操作", "转账"],
                "warning": "高风险，涉及金额较大",
                "is_error": False,
                "roles": ["嫌疑人", "受害人"],
                "extracted_entities": {
                    "bank_accounts": ["6222****5678"],
                    "phone_numbers": ["170****5678"],
                    "ip_addresses": ["183.214.***.***"],
                    "app_names": ["腾讯会议", "京东金融"],
                    "threat_intel": {
                        "bank_account_risk": "high",
                        "ip_location": "湖南省长沙市"
                    }
                }
            },
            {
                "case_id": "CASE_002", 
                "message_count": 10,
                "time_range": "15 - 24",
                "risk_level": "MEDIUM",
                "risk_label": "中风险",
                "risk_type": "warning",
                "risk_score": 75,
                "scam_type": "网络兼职",
                "victim": "李四",
                "amount": "¥8,000",
                "ai_report": "该案件为网络兼职诈骗...",
                "keywords": ["兼职", "刷单", "佣金"],
                "steps": ["看到兼职广告", "完成任务", "要求垫付"],
                "warning": "中风险，涉及刷单",
                "is_error": False,
                "roles": ["嫌疑人", "受害人"],
                "extracted_entities": {
                    "bank_accounts": [],
                    "phone_numbers": ["138****8888"],
                    "ip_addresses": [],
                    "app_names": ["抖音"],
                    "threat_intel": {
                        "bank_account_risk": "medium",
                        "ip_location": "广东省深圳市"
                    }
                }
            },
            {
                "case_id": "CASE_003",
                "message_count": 8,
                "time_range": "25 - 32",
                "risk_level": "LOW",
                "risk_label": "低风险",
                "risk_type": "info",
                "risk_score": 45,
                "scam_type": "虚假投资",
                "victim": "王五",
                "amount": "¥2,000",
                "ai_report": "该案件为虚假投资诈骗...",
                "keywords": ["投资", "高收益", "平台"],
                "steps": ["看到投资广告", "注册平台", "小额投资"],
                "warning": "低风险，涉及金额较小",
                "is_error": False,
                "roles": ["嫌疑人", "受害人"],
                "extracted_entities": {
                    "bank_accounts": ["6217****1234"],
                    "phone_numbers": [],
                    "ip_addresses": ["220.181.***.***"],
                    "app_names": ["微信"],
                    "threat_intel": {
                        "bank_account_risk": "low",
                        "ip_location": "浙江省杭州市"
                    }
                }
            }
        ],
        "gangs": [
            {
                "gang_id": "GANG_001",
                "gang_name": "客服诈骗团伙",
                "risk_level": "HIGH",
                "risk_label": "高风险",
                "risk_type": "danger",
                "confidence": 90,
                "member_count_estimate": "5-10人",
                "active_time": "24小时",
                "tech_level": "高",
                "script_type": "冒充客服",
                "total_cases": 2,
                "total_amount_involved": "¥58,000",
                "related_cases": ["CASE_001", "CASE_002"],
                "fingerprint": ["客服", "退款", "验证码", "兼职"],
                "steps": ["冒充客服", "诱导操作", "要求转账"],
                "description": "该团伙主要通过冒充客服进行诈骗，手法娴熟，涉及金额较大",
                "network_nodes": [
                    {"id": "1", "name": "主谋", "type": "leader", "risk": "high"},
                    {"id": "2", "name": "话务员", "type": "member", "risk": "medium"},
                    {"id": "3", "name": "收款人", "type": "member", "risk": "medium"}
                ],
                "radar_data": {
                    "indicator": [
                        {"name": "技术能力", "value": 85},
                        {"name": "组织严密性", "value": 75},
                        {"name": "反侦察能力", "value": 80},
                        {"name": "社会危害", "value": 90},
                        {"name": "作案频率", "value": 70},
                        {"name": "隐蔽性", "value": 65}
                    ],
                    "series_data": [85, 75, 80, 90, 70, 65]
                },
                "enhanced_fingerprint": ["客服", "退款", "验证码", "兼职", "高风险操作", "多起案件"],
                "comprehensive_score": 85,
                "threat_level": "S"
            },
            {
                "gang_id": "GANG_002",
                "gang_name": "投资诈骗团伙",
                "risk_level": "MEDIUM",
                "risk_label": "中风险",
                "risk_type": "warning",
                "confidence": 75,
                "member_count_estimate": "3-5人",
                "active_time": "白天",
                "tech_level": "中",
                "script_type": "虚假投资",
                "total_cases": 1,
                "total_amount_involved": "¥2,000",
                "related_cases": ["CASE_003"],
                "fingerprint": ["投资", "高收益", "平台"],
                "steps": ["发布广告", "诱导注册", "小额投资"],
                "description": "该团伙主要通过虚假投资平台进行诈骗，涉及金额较小",
                "network_nodes": [
                    {"id": "4", "name": "操盘手", "type": "leader", "risk": "medium"},
                    {"id": "5", "name": "推广员", "type": "member", "risk": "low"}
                ],
                "radar_data": {
                    "indicator": [
                        {"name": "技术能力", "value": 60},
                        {"name": "组织严密性", "value": 55},
                        {"name": "反侦察能力", "value": 50},
                        {"name": "社会危害", "value": 65},
                        {"name": "作案频率", "value": 45},
                        {"name": "隐蔽性", "value": 60}
                    ],
                    "series_data": [60, 55, 50, 65, 45, 60]
                },
                "enhanced_fingerprint": ["投资", "高收益", "平台", "中等风险"],
                "comprehensive_score": 60,
                "threat_level": "B"
            }
        ],
        "data_quality": {
            "completeness": 0.95,
            "suspiciousness": 0.82,
            "has_platform_clues": True,
            "overall_score": 0.885
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.route('/agent-analyze', methods=['POST'])
def agent_analyze():
    """
    智能分析接口（模拟）
    """
    try:
        data = request.json
        messages = data.get('messages', [])
        platform_data = data.get('platform_data', {})
        
        if not messages and not platform_data:
            return jsonify({"error": "没有收到消息内容或平台数据"}), 400
        
        print(f"收到分析请求，消息数: {len(messages)}")
        
        # 模拟处理延迟
        time.sleep(2)
        
        # 返回模拟数据
        response = get_mock_response()
        return jsonify(response)
        
    except Exception as e:
        print(f"分析失败: {e}")
        return jsonify({"error": f"分析失败: {str(e)}"}), 500

@app.route('/upload', methods=['POST'])
def upload_and_analyze():
    """
    传统分析接口（模拟）
    """
    try:
        data = request.json
        messages = data.get('messages', [])
        platform_data = data.get('platform_data', {})
        
        if not messages and not platform_data:
            return jsonify({"error": "没有收到消息内容或平台数据"}), 400
        
        print(f"收到上传请求，消息数: {len(messages)}")
        
        # 模拟处理延迟
        time.sleep(1)
        
        # 返回简化的模拟数据
        response = {
            "success": True,
            "total_cases": 3,
            "triage_status": "success",
            "has_errors": False,
            "cases": get_mock_response()["cases"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return jsonify(response)
        
    except Exception as e:
        print(f"分析失败: {e}")
        return jsonify({"error": f"分析失败: {str(e)}"}), 500

if __name__ == '__main__':
    print("[INFO] 简化版后端服务启动中...")
    print("[INFO] 服务地址: http://localhost:5000")
    print("[INFO] 提供模拟数据，用于前端开发测试")
    app.run(host='0.0.0.0', port=5000, debug=True)
