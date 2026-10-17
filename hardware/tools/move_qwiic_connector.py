"""Move J3 to the lower board edge with its cable entry facing outward.

The SMT footprint move does not preserve its connected route ends. This helper
removes only J3's old branch tracks; export a fresh DSN, autoroute the resulting
airwires, import the SES, then refill zones and run DRC.
"""

from pathlib import Path

import pcbnew

PCB = Path(__file__).resolve().parent.parent / "rpi-camera-led.kicad_pcb"
MM = pcbnew.FromMM

OLD_PAD_TRACKS = [
    ("GND", (19.0, 47.2424), (19.0, 48.5)),
    ("SCL", (16.0, 47.2339), (16.0, 48.5)),
    ("SDA", (17.0, 48.8964), (17.0, 48.5)),
    ("SDA", (17.0, 48.5), (17.0, 39.0788)),
    ("3V3", (18.0, 48.5), (18.0, 39.6918)),
]


def point_mm(point):
    return pcbnew.ToMM(point.x), pcbnew.ToMM(point.y)


def same_segment(track, endpoints):
    a, b = point_mm(track.GetStart()), point_mm(track.GetEnd())
    expected_a, expected_b = endpoints

    def near(point, expected):
        return abs(point[0] - expected[0]) < 0.01 and abs(point[1] - expected[1]) < 0.01

    return (near(a, expected_a) and near(b, expected_b)) or (
        near(a, expected_b) and near(b, expected_a)
    )


def main():
    board = pcbnew.LoadBoard(str(PCB))
    j3 = board.FindFootprintByReference("J3")
    if j3 is None:
        raise RuntimeError("J3 is missing from the PCB")
    position = (pcbnew.ToMM(j3.GetPosition().x), pcbnew.ToMM(j3.GetPosition().y))
    if abs(position[0] - 17.5) > 0.01:
        raise RuntimeError(f"J3 is not on the expected x coordinate: {position}")

    if abs(position[1] - 50.5) < 0.01:
        if abs(j3.GetOrientationDegrees() - 180) > 0.01:
            raise RuntimeError("J3 has an unexpected orientation at its original position")
        removed = set()
        for track in list(board.GetTracks()):
            net = track.GetNetname()
            for index, (expected_net, a, b) in enumerate(OLD_PAD_TRACKS):
                if net == expected_net and same_segment(track, (a, b)):
                    board.Delete(track)
                    removed.add(index)
                    break
        missing = set(range(len(OLD_PAD_TRACKS))) - removed
        if missing:
            raise RuntimeError(f"Expected J3 pad track segment(s) not found: {sorted(missing)}")
    elif abs(position[1] - 54.925) > 0.01 or abs(j3.GetOrientationDegrees()) > 0.01:
        raise RuntimeError(f"J3 is not at a recognized pre-move position: {position}")

    j3.SetPosition(pcbnew.VECTOR2I(MM(17.5), MM(53.7)))
    j3.SetOrientationDegrees(180)
    j3.Reference().SetPosition(pcbnew.VECTOR2I(MM(17.5), MM(51.1)))

    pcbnew.SaveBoard(str(PCB), board)
    print("Moved J3 to (17.5, 53.7), orientation 180: cable entry faces the board edge.")
    print("Removed only J3's old pad stubs; autoroute the resulting airwires.")


if __name__ == "__main__":
    main()
