import json
from copy import deepcopy
from pathlib import Path
from typing import List

from .Case import Outcome, Case


class Results:
    """
    Parses pytest-json-report results and exposes their content.
    Provides debug string concatenating test case results information.
    """

    def __init__(self, testRoot: str, cases: List[Case]) -> None:
        self.testRoot = testRoot
        self._testCases = cases

    @classmethod
    def fromReportFile(cls, jsonReportPath: Path):
        """
        :param jsonReportPath: Path to the JSON file containing the test results (collected or ran) as generated by
         the pytest-json-report plugin.
        """

        if not jsonReportPath.exists():
            return cls(f"results_not_found : {jsonReportPath}", [])

        with open(jsonReportPath, "r") as f:
            results_dict = json.loads(f.read())

        testRoot = results_dict.get("root")

        executedCases = [Case.fromExecutedTestDict(case) for case in results_dict.get("tests", [])]
        executedIds = {case.nodeid for case in executedCases}

        collectedCases = [
            Case.fromCollectedTestDict(case) for case in
            cls._extractCollectorResultsFromDict(results_dict)
        ]
        return cls(testRoot, executedCases + [case for case in collectedCases if case.nodeid not in executedIds])

    @staticmethod
    def _extractCollectorResultsFromDict(results_dict):
        collectedCases = []
        for collector in results_dict.get("collectors", []):
            if collector.get("outcome") == "failed":
                collectedCases.append(collector)

            for case_result in collector.get("result", []):
                if case_result["nodeid"].endswith("__init__.py"):
                    continue

                if case_result.get("type", "") not in ["Module", "UnitTestCase"]:
                    collectedCases.append(case_result)

        return collectedCases

    def getAllCases(self) -> List[Case]:
        return deepcopy(self._testCases)

    def getFailingCases(self) -> List[Case]:
        return [case for case in self._testCases if case.outcome in Outcome.failedOutcomes()]

    def getFailingCasesString(self):
        return "\n".join([case.getDebugString() for case in self.getFailingCases()])

    def getSummaryString(self):
        if not self.executedNumber:
            return "No tests to display." if not self.collectedNumber else f"collected:{self.collectedNumber} tests."

        passed = f"passed: {self.passedNumber}" if self.passedNumber else ""
        failed = f"failed: {self.failuresNumber}" if self.failuresNumber else ""
        ignored = f"ignored: {self.skippedNumber}" if self.skippedNumber else ""
        tests = ", ".join([test for test in [failed, ignored, passed] if test])
        return f"Tests {tests} of {self.executedNumber} tests."

    @property
    def executedNumber(self):
        return self.countCaseWithOutcome(Outcome.executedOutcomes())

    @property
    def collectedNumber(self):
        return self.countCaseWithOutcome(Outcome.collectedOutcomes())

    @property
    def passedNumber(self):
        return self.countCaseWithOutcome(Outcome.passedOutcomes())

    @property
    def failuresNumber(self):
        return self.countCaseWithOutcome(Outcome.failedOutcomes())

    @property
    def skippedNumber(self):
        return self.countCaseWithOutcome(Outcome.ignoredOutcomes())

    def countCaseWithOutcome(self, outcomes: List[Outcome]):
        return len([c for c in self._testCases if c.outcome in outcomes])
