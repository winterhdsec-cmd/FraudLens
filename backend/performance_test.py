"""
FraudLens 系统性能测试脚本
测试项目：
1. API 响应时间
2. 并发处理能力
3. 吞吐量
4. 错误率
5. 资源使用情况
"""
import asyncio
import aiohttp
import time
import statistics
from typing import Dict, List
from datetime import datetime
import json


class PerformanceTester:
    def __init__(self, base_url: str = "http://localhost:5003"):
        self.base_url = base_url
        self.results = {}
        
    async def test_single_endpoint(
        self, 
        session: aiohttp.ClientSession,
        method: str,
        endpoint: str,
        data: Dict = None,
        headers: Dict = None
    ) -> Dict:
        """测试单个端点的响应时间"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method == "GET":
                async with session.get(url, headers=headers, timeout=30) as response:
                    await response.text()
                    elapsed = time.time() - start_time
                    return {
                        "success": response.status == 200,
                        "status_code": response.status,
                        "response_time": elapsed,
                        "endpoint": endpoint
                    }
            elif method == "POST":
                async with session.post(url, json=data, headers=headers, timeout=30) as response:
                    await response.text()
                    elapsed = time.time() - start_time
                    return {
                        "success": response.status == 200,
                        "status_code": response.status,
                        "response_time": elapsed,
                        "endpoint": endpoint
                    }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "success": False,
                "status_code": 0,
                "response_time": elapsed,
                "endpoint": endpoint,
                "error": str(e)
            }
    
    async def test_endpoint_concurrent(
        self,
        endpoint: str,
        method: str = "GET",
        data: Dict = None,
        concurrent_requests: int = 10,
        total_requests: int = 50
    ) -> Dict:
        """测试端点的并发处理能力"""
        print(f"\n{'='*60}")
        print(f"测试端点: {endpoint}")
        print(f"并发数: {concurrent_requests}, 总请求数: {total_requests}")
        print(f"{'='*60}")
        
        async with aiohttp.ClientSession() as session:
            # 先获取 JWT token（如果需要认证）
            token = None
            if "chat" in endpoint or "cases" in endpoint:
                try:
                    async with session.post(
                        f"{self.base_url}/api/auth/login",
                        json={"username": "admin", "password": "admin123"},
                        timeout=10
                    ) as resp:
                        if resp.status == 200:
                            data_resp = await resp.json()
                            token = data_resp.get("access_token")
                except:
                    pass
            
            headers = {"Authorization": f"Bearer {token}"} if token else None
            
            # 执行并发请求
            tasks = []
            for _ in range(total_requests):
                task = self.test_single_endpoint(
                    session, method, endpoint, data, headers
                )
                tasks.append(task)
            
            # 分批执行（模拟并发）
            results = []
            batch_size = concurrent_requests
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i+batch_size]
                batch_results = await asyncio.gather(*batch)
                results.extend(batch_results)
            
            # 统计结果
            response_times = [r["response_time"] for r in results if r["success"]]
            success_count = sum(1 for r in results if r["success"])
            error_count = len(results) - success_count
            
            stats = {
                "endpoint": endpoint,
                "method": method,
                "total_requests": len(results),
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": f"{(success_count/len(results)*100):.2f}%",
                "concurrent_requests": concurrent_requests,
                "response_times": {
                    "min": min(response_times) if response_times else 0,
                    "max": max(response_times) if response_times else 0,
                    "avg": statistics.mean(response_times) if response_times else 0,
                    "median": statistics.median(response_times) if response_times else 0,
                    "p95": sorted(response_times)[int(len(response_times)*0.95)] if len(response_times) > 1 else 0,
                    "p99": sorted(response_times)[int(len(response_times)*0.99)] if len(response_times) > 1 else 0,
                },
                "throughput": f"{len(response_times)/sum(response_times):.2f} req/s" if response_times else "0 req/s"
            }
            
            print(f"✓ 成功请求: {success_count}/{len(results)}")
            print(f"✓ 成功率: {stats['success_rate']}")
            print(f"✓ 平均响应时间: {stats['response_times']['avg']*1000:.2f}ms")
            print(f"✓ P95 响应时间: {stats['response_times']['p95']*1000:.2f}ms")
            print(f"✓ P99 响应时间: {stats['response_times']['p99']*1000:.2f}ms")
            print(f"✓ 吞吐量: {stats['throughput']}")
            
            return stats
    
    async def run_all_tests(self):
        """运行所有性能测试"""
        print("\n" + "="*60)
        print("FraudLens 系统性能测试")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"目标服务器: {self.base_url}")
        print("="*60)
        
        # 测试 1: 健康检查端点（无认证）
        self.results["health"] = await self.test_endpoint_concurrent(
            "/health",
            method="GET",
            concurrent_requests=10,
            total_requests=50
        )
        
        # 测试 2: 案件列表查询（需要认证）
        self.results["cases_list"] = await self.test_endpoint_concurrent(
            "/api/cases?page=1&per_page=10",
            method="GET",
            concurrent_requests=5,
            total_requests=30
        )
        
        # 测试 3: 统计数据接口
        self.results["statistics"] = await self.test_endpoint_concurrent(
            "/api/dashboard",
            method="GET",
            concurrent_requests=5,
            total_requests=30
        )
        
        # 测试 4: 聊天接口（POST，需要认证）
        self.results["chat"] = await self.test_endpoint_concurrent(
            "/api/chat/message",
            method="POST",
            data={"message": "你好", "session_id": None},
            concurrent_requests=3,
            total_requests=15
        )
        
        # 测试 5: 团伙检测接口
        self.results["gangs"] = await self.test_endpoint_concurrent(
            "/api/gangs",
            method="GET",
            concurrent_requests=3,
            total_requests=20
        )
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成性能测试报告"""
        print("\n" + "="*60)
        print("性能测试报告")
        print("="*60)
        
        # 总体统计
        total_requests = sum(r["total_requests"] for r in self.results.values())
        total_success = sum(r["success_count"] for r in self.results.values())
        total_errors = sum(r["error_count"] for r in self.results.values())
        
        print(f"\n【总体统计】")
        print(f"总请求数: {total_requests}")
        print(f"成功请求: {total_success}")
        print(f"失败请求: {total_errors}")
        print(f"总体成功率: {(total_success/total_requests*100):.2f}%")
        
        # 各端点性能对比
        print(f"\n【各端点性能对比】")
        print(f"{'端点':<30} {'平均响应':<15} {'P95':<15} {'吞吐量':<15} {'成功率':<10}")
        print("-" * 85)
        
        for endpoint, stats in self.results.items():
            avg_time = f"{stats['response_times']['avg']*1000:.2f}ms"
            p95_time = f"{stats['response_times']['p95']*1000:.2f}ms"
            throughput = stats['throughput']
            success_rate = stats['success_rate']
            
            print(f"{endpoint:<30} {avg_time:<15} {p95_time:<15} {throughput:<15} {success_rate:<10}")
        
        # 性能评级
        print(f"\n【性能评级】")
        avg_response_time = statistics.mean([
            r["response_times"]["avg"] for r in self.results.values()
        ])
        
        if avg_response_time < 0.1:
            rating = "优秀 (A)"
            comment = "系统响应速度极快，性能优异"
        elif avg_response_time < 0.5:
            rating = "良好 (B)"
            comment = "系统性能良好，可以满足生产需求"
        elif avg_response_time < 1.0:
            rating = "一般 (C)"
            comment = "系统性能一般，建议优化慢查询"
        else:
            rating = "较差 (D)"
            comment = "系统性能较差，需要立即优化"
        
        print(f"性能评级: {rating}")
        print(f"评价: {comment}")
        
        # 保存详细报告
        report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_time": datetime.now().isoformat(),
                "base_url": self.base_url,
                "summary": {
                    "total_requests": total_requests,
                    "success_count": total_success,
                    "error_count": total_errors,
                    "success_rate": f"{(total_success/total_requests*100):.2f}%"
                },
                "detailed_results": self.results,
                "rating": rating,
                "comment": comment
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ 详细报告已保存: {report_file}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='FraudLens 性能测试')
    parser.add_argument('--port', type=int, default=5003, help='服务端口号')
    args = parser.parse_args()
    
    base_url = f"http://localhost:{args.port}"
    print(f"目标服务器: {base_url}")
    
    tester = PerformanceTester(base_url=base_url)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
