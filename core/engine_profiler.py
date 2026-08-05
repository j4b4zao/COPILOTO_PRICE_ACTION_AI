from core.execution_timer import ExecutionTimer
from core.performance_report import PerformanceReport


class EngineProfiler:

    def execute(self, engine, context):

        timer = ExecutionTimer()

        timer.start()

        report = PerformanceReport()

        report.engine = engine.NAME

        try:

            context = engine.executar(context)

            report.success = True

        except Exception as e:

            report.success = False

            report.message = str(e)

            raise

        finally:

            report.execution_time = timer.stop()

        return context, report