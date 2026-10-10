import pandas as pd

from mls211 import FourParamLogisticFit, PolynomialFit, QuadraticFit


def test_4plfit():
    abs =pd.Series([0.087,0.093,0.147,0.334,0.621,1.294], name="Abs")
    blanked = abs - abs[0]
    blanked.name = "Blanked_Abs"
    df = pd.concat([
        pd.Series([0.1,150,300,750,1500,3000], name="Std"),
        abs,
        blanked
    ], axis=1)
    print(df)
    analyser = FourParamLogisticFit(df)
    model = analyser.fit("Std","Blanked_Abs")
    analyser.print_parameters(model)
    p1 = analyser.inv_four_pl(0.7, *model)
    p2 = analyser.inv_four_pl(0.055, *model)
    print(f"Patient 1: {p1:.0f} ng/L; Patient 2: {p2:.0f} ng/L")
    analyser.plot("Std","Blanked_Abs", model)
    # print(analyser.four_pl(3000, *model))
    # print(analyser.inv_four_pl(1.206, *model))

def test_quadraticfit():
    abs =pd.Series([0.087,0.093,0.147,0.334,0.621,1.294], name="Abs")
    blanked = abs - abs[0]
    blanked.name = "Blanked_Abs"
    df = pd.concat([
        pd.Series([0.0,150,300,750,1500,3000], name="Std"),
        abs,
        blanked
    ], axis=1)
    print(df)
    print("Quadratic fit")
    quadratic = QuadraticFit(df)
    qmodel = quadratic.fit("Std","Blanked_Abs")
    print(qmodel)
    p1 = quadratic.inv_quadratic_through_zero(0.7, *qmodel)
    p2 = quadratic.inv_quadratic_through_zero(0.055, *qmodel)
    r_squared = quadratic.r_squared_through_zero(df["Std"], df["Blanked_Abs"], *qmodel)
    print(f"Patient 1: {p1[0]:.0f} ng/L; Patient 2: {p2[0]:.0f} ng/L")
    print(f"R-squared: {r_squared:.4f}")
    #quadratic.plot("Std","Blanked_Abs", qmodel)

def test_polynomialfit():
    abs =pd.Series([0.087,0.093,0.147,0.334,0.621,1.294], name="Abs")
    blanked = abs - abs[0]
    blanked.name = "Blanked_Abs"
    df = pd.concat([
        pd.Series([0.0,150,300,750,1500,3000], name="Std"),
        abs,
        blanked
    ], axis=1)
    print(df)
    poly = PolynomialFit(df)
    model = poly.fit("Std","Blanked_Abs")
    print(model)
    r_squared = poly.r_squared(df["Std"], df["Blanked_Abs"], model)
    print(f"R-squared: {r_squared}")

if __name__=="__main__":
    test_4plfit()
    test_polynomialfit()
    test_quadraticfit()
