from zaslon_shared.quantum import QuantumEngine, TransmissionResult


def transmit(engine: QuantumEngine, **parameters) -> TransmissionResult:
    return engine.teleport_and_measure(**parameters)

