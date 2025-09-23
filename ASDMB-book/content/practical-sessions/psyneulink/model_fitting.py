import numpy as np
import pandas as pd
import psyneulink as pnl
from psyneulink.core.globals.utilities import set_global_seed

pnl_seed = 0
set_global_seed(pnl_seed)

class StroopPNL_PEC_Model:
    def __init__(self):
        # Layers
        self.WORD = pnl.P(input_shapes=2, name="WORD")
        self.COLOR = pnl.TransferMechanism(input_shapes=2, name="COLOR")
        self.HIDDEN = pnl.TransferMechanism(input_shapes=4, function=pnl.Logistic(), name="HIDDEN")
        self.RESP = pnl.TransferMechanism(input_shapes=2, function=pnl.Linear(), name="RESP")

        # Drift Diffusion Model
        self.DDM = pnl.DDM(name="DDM",
                           function=pnl.DriftDiffusionIntegrator(
                               noise=.25,
                               starting_value=0.0,
                               non_decision_time=0.0,
                               rate=.05,
                               threshold=1.),
                           output_ports=[pnl.DECISION_OUTCOME, pnl.RESPONSE_TIME],
                           )  # outputs: DECISION_VARIABLE, RESPONSE_TIME

        # Composition
        self.comp = pnl.Composition()
        self.comp.add_linear_processing_pathway([self.WORD, self.HIDDEN, self.RESP])
        self.comp.add_linear_processing_pathway([self.COLOR, self.HIDDEN, self.RESP])
        self.comp.add_node(self.DDM)

        # Map RESP -> DDM
        self.comp.add_projection(
            pnl.MappingProjection(matrix=[[-1.0],  # from RESP[0] to DDM input
                                          [1.0]]),  # from RESP[1] to DDM input
            sender=self.RESP, receiver=self.DDM
        )

        # Which output ports to fit to
        self.out_vars = [
            self.DDM.output_ports['DECISION_OUTCOME'],
            self.DDM.output_ports['RESPONSE_TIME'],
        ]

    def _inputs_from_X(self, X: pd.DataFrame):
        W = X[[c for c in X.columns if c.startswith("word_")]].to_numpy().tolist()
        C = X[[c for c in X.columns if c.startswith("color_")]].to_numpy().tolist()
        return {self.WORD: W, self.COLOR: C}

    # AutoRA expects predict and fit methods
    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        self.comp.run(inputs=self._inputs_from_X(X), num_trials=len(X))
        dec = [float(self.comp.results[t][0][0]) for t in range(len(X))]
        rt_s = [float(self.comp.results[t][1][0]) for t in range(len(X))]
        return pd.DataFrame({
            "decision_variable": dec,
            "rt_ms": np.array(rt_s) * 1000.0,
        })

    def fit(self, X: pd.DataFrame, y: pd.DataFrame, condition_col: str | None = None):
        # Ensure y columns align with outcome ports and datatypes
        y = y.copy()

        # Expect columns named exactly like the DDM output ports:
        #   DECISION_VARIABLE (categorical ±1), RESPONSE_TIME (seconds)
        if "DECISION_OUTCOME" not in y or "RESPONSE_TIME" not in y:
            raise ValueError("y must have columns: ['DECISION_VARIABLE', 'RESPONSE_TIME']")

        # Categorical for choice (per PEC docs)
        if not pd.api.types.is_categorical_dtype(y["DECISION_OUTCOME"]):
            y["DECISION_OUTCOME"] = pd.Categorical(y["DECISION_VARIABLE"])

        # Parameter grid (keys are (parameter_name, owner) tuples)
        params = {
            ('non_decision_time', self.comp.nodes['DDM']): list(np.linspace(0.0, 1.5, 8)),
        }

        # Optional conditioning (e.g., different thresholds per condition)
        depends = None
        if condition_col is not None:
            if condition_col not in y:
                raise ValueError(f"condition_col '{condition_col}' not found in y")
            depends = {('non_decision_time', self.comp.nodes['DDM']): 'condition'}

        pec = pnl.ParameterEstimationComposition(
            model=self.comp,
            parameters=params,
            outcome_variables=self.out_vars,
            # must be terminal ports
            data=y[["DECISION_OUTCOME", "RESPONSE_TIME", "condition"]] if condition_col else y[
                ["DECISION_OUTCOME", "RESPONSE_TIME"]],
            depends_on=depends,
            optimization_function="differential_evolution",
            initial_seed=42,
            same_seed_for_all_parameter_combinations=True,
        )
        # print("Controlled params -> targets")
        # for cs in pec.controller.control_signals:
        #     print(cs.name, "=>", [pp.owner.name + "." + pp.name for pp in cs.modulates])

        pec.run(inputs=self._inputs_from_X(X), num_trials=len(X))
        return pec.optimized_parameter_values


# ---------- synthetic binary Stroop data ----------
def gen_data(n=100, seed=0):
    rng = np.random.default_rng(seed)
    classes = np.array(["red", "green"])
    word = rng.choice(classes, size=n)
    color = rng.choice(classes, size=n, p=[0.5, 0.5])
    condition = np.where(word == color, "congruent", "incongruent")

    # Choices
    choose_color_p = np.where(condition == "congruent", 0.95, 0.65)
    choose_color = rng.random(n) < choose_color_p
    chosen_label = np.where(choose_color, color, word)

    # RTs (seconds)
    rt = np.where(condition == "congruent",
                  rng.normal(0.60, 0.08, size=n),
                  rng.normal(0.80, 0.12, size=n))
    rt = np.clip(rt, 0.2, None)

    # One-hot inputs
    df = pd.DataFrame({"word": word, "color": color, "condition": condition})
    df = pd.get_dummies(df, columns=["word", "color"], prefix=["word", "color"])

    # Target columns aligned to DDM ports
    sign = np.where(chosen_label == "green", 1.0, -1.0)  # map green->+1, red->-1
    df["DECISION_OUTCOME"] = pd.Categorical(sign)
    df["RESPONSE_TIME"] = rt  # seconds

    return df


if __name__ == "__main__":
    # Test
    data = gen_data()
    X = data[[c for c in data.columns if c.startswith("word_") or c.startswith("color_")]]
    y = data[["DECISION_OUTCOME", "RESPONSE_TIME"]]

    model = StroopPNL_PEC_Model()

    print("Fitting model...")
    best_params = model.fit(X, y)
    print("Best parameters:", best_params)

    print("\nPredicting with fitted model...")
    preds = model.predict(X)
    print(preds.head())
