"""Finish the two Qwiic airwires left by Freerouting after the J3 relocation."""

from pathlib import Path

import pcbnew

PCB = Path(__file__).resolve().parent.parent / "rpi-camera-led.kicad_pcb"
MM = pcbnew.FromMM


def xy(point):
    return pcbnew.VECTOR2I(MM(point[0]), MM(point[1]))


def add_track(board, net, start, end):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(xy(start))
    track.SetEnd(xy(end))
    track.SetWidth(MM(0.2))
    track.SetLayer(pcbnew.B_Cu)
    track.SetNetCode(net.GetNetCode())
    board.Add(track)


def add_via(board, net, position):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(xy(position))
    via.SetWidth(MM(0.6))
    via.SetDrill(MM(0.3))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNetCode(net.GetNetCode())
    board.Add(via)


def main():
    board = pcbnew.LoadBoard(str(PCB))
    j3 = board.FindFootprintByReference("J3")
    if j3 is None or abs(j3.GetOrientationDegrees() - 180) > 0.01:
        raise RuntimeError("J3 is not at the routed edge position")
    pads = {pad.GetNetname(): pad for pad in j3.Pads() if pad.GetNetname()}
    for net_name, expected in (("SDA", (17.0, 51.7)), ("3V3", (18.0, 51.7))):
        pad = pads.get(net_name)
        if pad is None or (
            abs(pcbnew.ToMM(pad.GetPosition().x) - expected[0]) > 0.01
            or abs(pcbnew.ToMM(pad.GetPosition().y) - expected[1]) > 0.01
        ):
            raise RuntimeError(f"J3 {net_name} pad is not at the expected position")
    if not any(
        t.GetNetname() == "SDA"
        and not isinstance(t, pcbnew.PCB_VIA)
        and abs(pcbnew.ToMM(t.GetEnd().x) - 17.8719) < 0.01
        and abs(pcbnew.ToMM(t.GetEnd().y) - 49.7683) < 0.01
        for t in board.GetTracks()
    ):
        raise RuntimeError("Expected SDA route endpoint from Freerouting was not found")
    if any(
        isinstance(t, pcbnew.PCB_VIA)
        and abs(pcbnew.ToMM(t.GetPosition().x) - 17.8) < 0.01
        and abs(pcbnew.ToMM(t.GetPosition().y) - 50.7) < 0.01
        for t in board.GetTracks()
    ):
        raise RuntimeError("The planned 3V3 via location is already occupied")

    sda = board.FindNet("SDA")
    rail = board.FindNet("3V3")
    if sda is None or rail is None:
        raise RuntimeError("SDA or 3V3 net is missing")
    add_track(board, sda, (17.0, 51.7), (17.0, 50.5))
    add_track(board, sda, (17.0, 50.5), (17.8, 49.7))
    add_track(board, sda, (17.8, 49.7), (17.8719, 49.7683))
    add_track(board, rail, (18.0, 51.7), (17.8, 51.5))
    add_track(board, rail, (17.8, 51.5), (17.8, 50.7))
    add_via(board, rail, (17.8, 50.7))

    j3.Reference().SetPosition(xy((12.5, 53.7)))
    pcbnew.SaveBoard(str(PCB), board)
    print("Completed J3 SDA and 3V3 connections and moved its silkscreen reference.")


if __name__ == "__main__":
    main()
