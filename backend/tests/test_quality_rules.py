
import unittest

from app.agent.quality import check_itinerary_quality


def make_state(activities, total_days=1):
    """构造用于测试的旅行规划状态。"""
    return {
        "itinerary": [
            {
                "day": 1,
                "activities": activities,
            }
        ],
        "parsed_requirements": {
            "total_days": total_days,
        },
    }


class TestQualityRules(unittest.TestCase):

    def test_overlapping_activities(self):
        """测试同一天活动时间重叠。"""
        state = make_state([
            {
                "place_name": "西湖",
                "start_time": "09:00",
                "end_time": "12:00",
            },
            {
                "place_name": "灵隐寺",
                "start_time": "10:00",
                "end_time": "11:30",
            },
        ])

        result = check_itinerary_quality(state)

        self.assertFalse(result["quality_passed"])
        self.assertTrue(
            any(
                "时间存在重叠" in warning
                for warning in result["quality_warnings"]
            )
        )

    def test_invalid_time_order(self):
        """测试结束时间早于开始时间。"""
        state = make_state([
            {
                "place_name": "西湖",
                "start_time": "15:00",
                "end_time": "13:00",
            }
        ])

        result = check_itinerary_quality(state)

        self.assertFalse(result["quality_passed"])
        self.assertTrue(
            any(
                "结束时间不能早于" in warning
                for warning in result["quality_warnings"]
            )
        )

    def test_incorrect_day_count(self):
        """测试生成行程天数与需求不一致。"""
        state = make_state(
            activities=[
                {
                    "place_name": "西湖",
                    "start_time": "09:00",
                    "end_time": "11:00",
                }
            ],
            total_days=3,
        )

        result = check_itinerary_quality(state)

        self.assertFalse(result["quality_passed"])
        self.assertTrue(
            any(
                "旅行天数不一致" in warning
                for warning in result["quality_warnings"]
            )
        )

    def test_valid_schedule(self):
        """测试正常行程可以通过质量检查。"""
        state = make_state([
            {
                "place_name": "西湖",
                "start_time": "09:00",
                "end_time": "11:00",
            },
            {
                "place_name": "灵隐寺",
                "start_time": "13:00",
                "end_time": "15:00",
            },
        ])

        result = check_itinerary_quality(state)

        self.assertTrue(result["quality_passed"])
        self.assertEqual(result["quality_score"], 100)


if __name__ == "__main__":
    unittest.main()
