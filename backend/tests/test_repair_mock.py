
import json
import unittest
from unittest.mock import MagicMock, patch

from app.agent.repair import repair_itinerary


def make_activity(name, start, end):
    return {
        "place_name": name,
        "start_time": start,
        "end_time": end,
        "description": "游览景点",
        "transport_suggestion": "步行",
    }


def make_state():
    return {
        "itinerary": [
            {
                "day": 1,
                "date": "2027-04-03",
                "theme": "杭州景点游览",
                "activities": [
                    make_activity("西湖", "09:00", "12:00"),
                    make_activity("灵隐寺", "10:00", "13:00"),
                ],
            }
        ],
        "parsed_requirements": {
            "total_days": 1,
            "daily_start_time": "08:00",
            "daily_end_time": "18:00",
        },
        "quality_passed": False,
        "quality_warnings": [
            "第1天的西湖与灵隐寺活动时间存在重叠"
        ],
        "retry_count": 0,
    }


def make_plan(second_place="灵隐寺"):
    return {
        "title": "杭州一日游",
        "destination": "杭州",
        "days": [
            {
                "day": 1,
                "date": "2027-04-03",
                "theme": "杭州景点游览",
                "activities": [
                    make_activity("西湖", "09:00", "11:00"),
                    make_activity(second_place, "13:00", "15:00"),
                ],
            }
        ],
    }


class TestRepairMock(unittest.TestCase):

    def run_with_mock(self, response_text):
        fake_llm = MagicMock()
        fake_llm.invoke.return_value.content = response_text

        with patch.dict(
            "os.environ",
            {
                "LLM_API_KEY": "test-key-not-real",
                "LLM_BASE_URL": "http://localhost/mock",
                "LLM_MODEL": "mock-model",
            },
        ):
            with patch(
                "app.agent.repair.ChatOpenAI",
                return_value=fake_llm,
            ):
                return repair_itinerary(make_state())

    def test_successful_repair(self):
        """AI 修复时间冲突后应通过质量检查。"""
        result = self.run_with_mock(
            json.dumps(make_plan(), ensure_ascii=False)
        )

        self.assertEqual(result["status"], "quality_checked")
        self.assertTrue(result["quality_passed"])
        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(result["quality_score"], 100)

    def test_reject_changed_place(self):
        """AI 擅自替换景点时应拒绝结果。"""
        result = self.run_with_mock(
            json.dumps(
                make_plan(second_place="雷峰塔"),
                ensure_ascii=False,
            )
        )

        self.assertEqual(
            result["status"],
            "quality_needs_improvement",
        )
        self.assertEqual(result["retry_count"], 1)
        self.assertIn(
            "改变了原有景点",
            result["error_message"],
        )

    def test_invalid_model_json(self):
        """AI 返回非法 JSON 时应安全处理。"""
        result = self.run_with_mock("not valid json")

        self.assertEqual(
            result["status"],
            "quality_needs_improvement",
        )
        self.assertEqual(result["retry_count"], 1)
        self.assertIn(
            "修正失败",
            result["error_message"],
        )


if __name__ == "__main__":
    unittest.main()
