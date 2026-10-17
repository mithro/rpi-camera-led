"""Complete the 3V3 connection that Freerouting cannot clear around the lens.

Run with KiCad's Python after importing the generated SES into the board.
"""

from pathlib import Path

import pcbnew

PCB = Path(__file__).resolve().parent.parent / "rpi-camera-led.kicad_pcb"
MM = pcbnew.FromMM


def add_track(board, net, layer, start, end):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pcbnew.VECTOR2I(MM(start[0]), MM(start[1])))
    track.SetEnd(pcbnew.VECTOR2I(MM(end[0]), MM(end[1])))
    track.SetWidth(MM(0.2))
    track.SetLayer(layer)
    track.SetNetCode(net.GetNetCode())
    board.Add(track)


def add_via(board, net, position):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(MM(position[0]), MM(position[1])))
    via.SetWidth(MM(0.6))
    via.SetDrill(MM(0.3))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNetCode(net.GetNetCode())
    board.Add(via)


def main():
    board = pcbnew.LoadBoard(str(PCB))
    net = board.FindNet("3V3")
    if net is None:
        raise RuntimeError("3V3 net is missing from the board")
    generated_segments = {
        ((18.0, 39.6918), (18.0, 15.5)),
        ((18.0, 15.5), (26.2, 15.5)),
        ((26.2, 15.5), (26.2, 19.025)),
        ((26.2, 19.025), (26.675, 19.5)),
        ((18.0, 39.6918), (18.5, 39.0)),
        ((18.5, 39.0), (18.5, 15.5)),
        ((18.5, 15.5), (26.2, 15.5)),
        ((26.2, 15.5), (25.7, 20.5)),
        ((18.0, 39.6918), (18.4, 39.0)),
        ((18.4, 39.0), (18.4, 15.5)),
        ((18.4, 15.5), (26.2, 15.5)),
    }
    for track in list(board.GetTracks()):
        if track.GetNetname() != "3V3":
            continue
        if isinstance(track, pcbnew.PCB_VIA):
            x = pcbnew.ToMM(track.GetPosition().x)
            y = pcbnew.ToMM(track.GetPosition().y)
            if (abs(x - 26.2) < 0.01 and abs(y - 15.5) < 0.01) or (
                abs(x - 25.7) < 0.01 and abs(y - 20.5) < 0.01
            ):
                board.Delete(track)
            continue
        start = track.GetStart()
        end = track.GetEnd()
        a = (round(pcbnew.ToMM(start.x), 4), round(pcbnew.ToMM(start.y), 4))
        b = (round(pcbnew.ToMM(end.x), 4), round(pcbnew.ToMM(end.y), 4))
        if (a, b) in generated_segments or (b, a) in generated_segments:
            board.Delete(track)

    pad = next(
        pad
        for footprint in board.GetFootprints()
        if footprint.GetReference() == "R3"
        for pad in footprint.Pads()
        if pad.GetNumber() == "1" and pad.GetNetname() == "3V3"
    )
    pad_x = pcbnew.ToMM(pad.GetPosition().x)
    pad_y = pcbnew.ToMM(pad.GetPosition().y)

    add_track(board, net, pcbnew.B_Cu, (18.0, 39.6918), (18.4, 39.0))
    add_track(board, net, pcbnew.B_Cu, (18.4, 39.0), (18.4, 15.5))
    add_track(board, net, pcbnew.B_Cu, (18.4, 15.5), (26.2, 15.5))
    add_track(board, net, pcbnew.B_Cu, (26.2, 15.5), (25.7, 20.5))
    add_via(board, net, (25.7, 20.5))
    add_track(board, net, pcbnew.F_Cu, (25.7, 20.5), (pad_x, pad_y))

    pcbnew.SaveBoard(str(PCB), board)
    print(f"Completed 3V3 route to R3-1 in {PCB}")


if __name__ == "__main__":
    main()
