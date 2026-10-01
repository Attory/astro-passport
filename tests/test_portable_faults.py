"""Supplement-specific native failures; stubs are NOT numerical references."""

import datetime as dt

import pytest

from app.science.ephemeris import worker


@pytest.mark.parametrize(
    "fault", [None, "flags", "warning", "nonfinite", "file", "generation", "range"]
)
def test_speed_supplement_never_accepts_fallback_or_bad_native_values(tmp_path, monkeypatch, fault):
    calls = []

    class Library:
        TIDAL_DE441, DELTAT_AUTOMATIC, GREG_CAL = 441, 0, 1
        SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO, TRUE_NODE = range(
            11
        )
        Error = RuntimeError

        def set_ephe_path(self, _):
            pass

        def set_tid_acc(self, _):
            pass

        def set_delta_t_userdef(self, _):
            pass

        def julday(self, *args):
            return 2451545.0

        def deltat_ex(self, *args):
            return 0.001, ""

        def close(self):
            pass

        def calc(self, _jd, body, flags):
            calls.append((body, flags))
            values = (float(body), 0.0, 1.0, 0.1, 0.0, 0.0)
            if flags == 258:
                if fault == "flags":
                    return values, 260, ""
                if fault == "warning":
                    return values, flags, "synthetic warning"
                if fault == "nonfinite":
                    return (*values[:3], float("nan"), 0.0, 0.0), flags, ""
            return values, flags, ""

        def houses_ex(self, *args):
            assert len(calls) == 13 and all(flag == 2 for _, flag in calls)
            return (0.0,) + tuple(float(i * 30) for i in range(12)), (0.0,) * 8

        def get_current_file_data(self, index):
            assert len([c for c in calls if c[1] == 258]) == 11
            filename = (
                "wrong" if fault == "file" else "sepl_18.se1" if index == 0 else "semo_18.se1"
            )
            return (
                str(tmp_path / filename),
                2499999 if fault == "range" else 2400000,
                2500000,
                440 if fault == "generation" else 441,
            )

    monkeypatch.setattr(worker, "_library", lambda: Library())
    if fault is None:
        result = worker.run(
            dt.datetime(2000, 1, 1, tzinfo=dt.UTC), tmp_path, western=(0.0, 0.0), kinematics=True
        )
        assert result["western"]["kinematics"]["returned_flags"] == [258] * 11
        assert [flag for _, flag in calls] == [2] * 13 + [258] * 11
    else:
        with pytest.raises(worker.WorkerFailure) as failure:
            worker.run(
                dt.datetime(2000, 1, 1, tzinfo=dt.UTC),
                tmp_path,
                western=(0.0, 0.0),
                kinematics=True,
            )
        assert str(failure.value) == (
            "native_failure" if fault in {"warning", "nonfinite"} else "fallback_rejected"
        )
