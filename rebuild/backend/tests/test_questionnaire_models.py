"""问卷模型的数据完整性测试：使用内存 SQLite，不连接项目 MySQL。"""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import create_engine, event
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateIndex, CreateTable

from app.database import Base
from app.models import (
    Candidate, Questionnaire, QuestionnaireResponse, QuestionnaireTemplate,
)


class QuestionnaireModelsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)
        self.candidate = Candidate(name="测试候选人", position="Python 开发")
        self.template = QuestionnaireTemplate(
            title="Python 基础评估",
            job_category="python",
            questions=[{"id": 1, "type": "text", "question": "解释异步等待。"}],
        )
        self.session.add_all([self.candidate, self.template])
        self.session.commit()

    def make_questionnaire(self):
        # 这里显式复制题目；后续发送服务也需要执行这一步。
        questionnaire = Questionnaire(
            candidate_id=self.candidate.id,
            template_id=self.template.id,
            title=self.template.title,
            questions=deepcopy(self.template.questions),
        )
        self.session.add(questionnaire)
        self.session.commit()
        return questionnaire

    def test_template_question_count_and_defaults_round_trip(self):
        self.assertEqual(self.template.question_count, 1)
        self.assertTrue(self.template.is_active)
        self.assertIsNotNone(self.template.created_at)
        self.assertIsNone(self.template.created_at.tzinfo)
        self.template.questions = self.template.questions + [
            {"id": 2, "type": "text", "question": "解释数据库索引。"}
        ]
        self.session.commit()
        self.session.expire_all()
        self.assertEqual(self.template.question_count, 2)

    def test_template_edit_preserves_issued_question_snapshot(self):
        questionnaire = self.make_questionnaire()
        original = deepcopy(questionnaire.questions)
        self.template.questions = [{"id": 1, "question": "新版本题目"}]
        self.session.commit()
        self.session.expire_all()
        self.assertEqual(questionnaire.questions, original)
        self.assertNotEqual(questionnaire.questions, self.template.questions)

    def test_deleting_template_keeps_questionnaire_and_snapshot(self):
        questionnaire = self.make_questionnaire()
        questionnaire_id = questionnaire.id
        snapshot = deepcopy(questionnaire.questions)
        self.session.delete(self.template)
        self.session.commit()
        self.session.expire_all()
        stored = self.session.get(Questionnaire, questionnaire_id)
        self.assertIsNotNone(stored)
        self.assertIsNone(stored.template_id)
        self.assertEqual(stored.questions, snapshot)

    def test_response_json_and_ungraded_state_round_trip(self):
        questionnaire = self.make_questionnaire()
        response = QuestionnaireResponse(
            questionnaire_id=questionnaire.id,
            candidate_id=self.candidate.id,
            answers={"1": "等待 I/O 时允许执行其他任务。"},
        )
        self.session.add(response)
        self.session.commit()
        self.session.expire_all()
        self.assertEqual(response.answers["1"], "等待 I/O 时允许执行其他任务。")
        self.assertIsNone(response.score)
        self.assertIsNone(response.passed)
        self.assertIsNotNone(response.created_at)

    def test_missing_template_is_rejected_by_foreign_key(self):
        self.session.add(Questionnaire(
            candidate_id=self.candidate.id, template_id=999999, questions=[],
        ))
        with self.assertRaises(IntegrityError):
            self.session.flush()
        self.session.rollback()

    def test_missing_candidate_is_rejected_by_foreign_key(self):
        self.session.add(Questionnaire(
            candidate_id=999999, template_id=self.template.id, questions=[],
        ))
        with self.assertRaises(IntegrityError):
            self.session.flush()
        self.session.rollback()

    def test_all_tables_and_indexes_compile_for_mysql(self):
        for table in Base.metadata.sorted_tables:
            str(CreateTable(table).compile(dialect=mysql.dialect()))
            for index in table.indexes:
                str(CreateIndex(index).compile(dialect=mysql.dialect()))


if __name__ == "__main__":
    unittest.main()
