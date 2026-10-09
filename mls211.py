import argparse
import math
import pathlib
from decimal import ROUND_HALF_UP, Decimal
from io import StringIO

import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
from scipy.optimize import curve_fit

DEFAULT_INPUT_FILE = "./Task 1a/task1atable3.txt"
DEFAULT_EXCEL_FILE = "./Task 1a/Task 1a.xlsx"

class TableConverter:
    """A class to convert space-separated text files into an array (rows) of arrays (columns)."""

    def __init__(self):
        pass

    def read_file(self, input_path: pathlib.Path) -> pd.DataFrame:
        """Read a space-separated text file and return its contents as a 2D list of numbers."""
        with input_path.open("r", encoding="utf-8") as infile:
            df = pd.read_csv(infile, sep=" ", header=None)
            return df

    def text_to_pandas_dataframe(self, text) -> pd.DataFrame:
        """Convert a space-separated text string into a pandas DataFrame."""

        # Use StringIO to treat the string as a file-like object
        data = StringIO(text)
        df = pd.read_csv(data, sep=" ", header=None)
        return df
    

class ExcelWriter:
    """A class to write data to an Excel file."""

    def __init__(self):
        pass

    def write_dataframe_to_excel(self, df: pd.DataFrame, output_path: pathlib.Path, sheet_name:str, col_offset:int=0, row_offset:int=0) -> None:
        """Write a 2D list of data to an Excel file."""
        if output_path.exists():
            workbook = openpyxl.load_workbook(output_path)
        else:
            raise FileNotFoundError(f"Excel file not found: {output_path.resolve()}")
        sheet = workbook[sheet_name]

        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                value = df.iloc[row, col]
                sheet.cell(row=row + row_offset, column=col + col_offset, value=value)

        workbook.save(output_path)

class StandardCurveBuilder:
    """Build the standard curve from the aborbances and known values"""
    def __init__(self):
        self.df: pd.DataFrame = None

    def set_dataframe(self, df: pd.DataFrame):
        self.df = df
        return self

    def read(self, text:str):
        # Use StringIO to treat the string as a file-like object
        data = StringIO(text)
        self.df = pd.read_csv(data, sep=" ", header=None)
        return self

    def set_colnames(self, colnames: list[str]):
        if not len(colnames) == self.df.shape[1]:
            raise ValueError(f"Expected {len(colnames)} columns but data contains {self.df.shape[1]}.")
        else:
            self.df.columns = colnames
        return self

    def calc_abs_means(self, absorbance_cols: list[str]):
        self.df["Mean_Abs"] = self.df.loc[:, absorbance_cols].mean(axis=1)
        self.df["Blanked_Abs"] = self.df['Mean_Abs'] - self.df['Mean_Abs'].iloc[0]
        return self

    def build(self) -> pd.DataFrame:
        return self.df

class StandardCurveAnalyser:
    """A class to analyze standard curves from pandas dataframe."""
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.slope = 0

    def linear_regression(self, std_col: str, abs_col:str) -> tuple[float, float]:
        x = self.df.loc[:, std_col].array
        y = self.df.loc[:, abs_col].array
        if len(x) != len(y):
            raise ValueError("x and y must have the same length.")
        # Reshape to a column matix for the least squares calculation
        X = x[:, np.newaxis]
        # Calculate the slope (m), forcing the intercept to be 0
        slope, _residuals, _rank, _s = np.linalg.lstsq(X, y, rcond=None)
        self.slope = slope[0]
        return (slope[0], 0)  # Return slope and intercept (0)

    def r_squared_forced_through_origin(self, std_col: str, abs_col:str) -> float:
        """Calculate R-squared for a linear regression forced through the origin."""
        x = self.df.loc[:, std_col].array
        y = self.df.loc[:, abs_col].array
        if len(x) != len(y):
            raise ValueError("x and y must have the same length.")
        slope, _ = self.linear_regression(std_col, abs_col)
        y_pred = slope * x
        ss_res = np.sum((y - y_pred) ** 2)
        #ss_tot = np.sum((y - np.mean(y)) ** 2)
        ss_tot = np.sum(y ** 2)
        r_squared = 1 - (ss_res / ss_tot)
        return r_squared

    def calculate_sample_concentration(self, df_samples: pd.DataFrame, col_conc: str, col_abs: str, dilution_factor: float) -> pd.DataFrame:
        df_samples[col_abs] = df_samples['Mean_Abs'] - self.df['Mean_Abs'].iloc[0]
        
        df_samples[col_conc] = df_samples[col_abs].div(self.slope).mul(dilution_factor)
        df_samples[col_conc] = df_samples[col_conc].round(1)
        return df_samples

def round_half_up(data: pd.Series, target_str: str) -> pd.Series:
    target = Decimal(target_str)
    data = data.apply(
        lambda x: Decimal(str(x)).quantize(target, rounding=ROUND_HALF_UP)
    )
    return data

class PolynomialFit:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def fit(self ,x_col:str, y_col:str):
        x_data = self.df[x_col]
        y_data = self.df[y_col]
        model = np.polynomial.Polynomial.fit(x_data,y_data, deg=[1,2], domain=[])
        return model

    def r_squared(self, x_data, y_data, model):
        y_pred = model(x_data)
        ss_res = np.sum((y_data - y_pred) ** 2)
        ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)
        return r_squared


class QuadraticFit:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    # Define quadratic function with no intercept (c = 0)
    def quadratic_through_zero(self, x, a, b):
        return a * x**2 + b * x

    def inv_quadratic_through_zero(self, y:float, a:float, b:float)->(float):
        return (((-1*b)+math.sqrt(b**2  + (4*a*y)))/(2*a), ((-1*b)-math.sqrt(b**2  + (4*a*y)))/(2*a))

    def fit(self,x_col:str, y_col:str)->(float):
        #np.random.seed(42)
        #x_data = np.array([0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0])
        x_data = self.df[x_col]
 
        # Add realistic noise
        y_data = self.df[y_col]

        # Fit the curve
        popt, _pcov = curve_fit(self.quadratic_through_zero, x_data, y_data)
        a_opt, b_opt = popt

        return (a_opt, b_opt)

    def r_squared_through_zero(self, x_data:pd.Series, y_data:pd.Series, a:float, b:float)->float:
        residuals = y_data - self.quadratic_through_zero(x_data, a, b)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)
        return 1- (ss_res/ss_tot)

    def plot(self, x_col:str, y_col:str, parameters: (float)):
        x_data = self.df[x_col]
        y_data = self.df[y_col]
        # 5. Plot the result
        x_smooth = np.arange(x_data.min(), x_data.max(), 1)
        y_smooth = self.quadratic_through_zero(x_smooth, *parameters)

        plt.figure(figsize=(8, 5))
        plt.scatter(x_data, y_data, color='red', label='Data Points', zorder=5)
        plt.plot(x_smooth, y_smooth, color='blue', label='Quadratic Fitted Curve', lw=2)
        plt.xlabel('Concentration / Dose (Log Scale)')
        plt.ylabel('Response / OD')
        plt.title('Quadratic Curve Fit')
        plt.legend()
        plt.grid(True, which="both", ls="--", alpha=0.5)
        plt.show()

class FourParamLogisticFit:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    # 1. Define the 4-parameter logistic function
    def four_pl(self, x, A, B, C, D):
        """
        A = Minimum asymptote
        B = Hill slope
        C = Inflection point (EC50)
        D = Maximum asymptote
        """
        return A + (D - A) / (1.0 + (x / C) ** B)

    def inv_four_pl(self, y, A, B, C, D):
        return C * ((((D-A)/(y-A))-1)**(1/B))

    def fit(self,x_col:str, y_col:str):
        #np.random.seed(42)
        #x_data = np.array([0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0])
        x_data = self.df[x_col]
 
        # Add realistic noise
        y_data = self.df[y_col]

        # 3. Provide initial guesses (Crucial for non-linear optimization convergence)
        # Guessing based on data attributes:
        initial_A = np.min(y_data).item()
        initial_B = 1.0  # Standard starting slope
        initial_C = np.median(x_data).item()  # Middle concentration
        initial_D = np.max(y_data).item()
        p0 = [initial_A, initial_B, initial_C, initial_D]

        # 4. Fit the curve
        # bounds can be added if parameters must stay positive: bounds=(0, np.inf)
        popt, _pcov = curve_fit(self.four_pl, x_data, y_data, p0=p0)

        # Extract optimized parameters
        fitted_A, fitted_B, fitted_C, fitted_D = popt

        return (fitted_A, fitted_B, fitted_C, fitted_D)

    def print_parameters(self, parameters: (float)):

        print("Fitted Parameters:")
        print(f"A (Min Asymptote): {parameters[0]:.4f}")
        print(f"B (Hill Slope)   : {parameters[1]:.4f}")
        print(f"C (EC50/IC50)    : {parameters[2]:.4f}")
        print(f"D (Max Asymptote): {parameters[3]:.4f}")

    def plot(self, x_col:str, y_col:str, parameters: (float)):
        x_data = self.df[x_col]
        y_data = self.df[y_col]
        # 5. Plot the result
        x_smooth = np.logspace(np.log10(x_data.min()), np.log10(x_data.max()), 200)
        y_smooth = self.four_pl(x_smooth, *parameters)

        plt.figure(figsize=(8, 5))
        plt.scatter(x_data, y_data, color='red', label='Data Points', zorder=5)
        plt.plot(x_smooth, y_smooth, color='blue', label='4PL Fitted Curve', lw=2)
        plt.xscale('log')  # Symmetrical S-shapes are best viewed on log-scale x-axes
        plt.xlabel('Concentration / Dose (Log Scale)')
        plt.ylabel('Response / OD')
        plt.title('4-Parameter Logistic (4PL) Curve Fit')
        plt.legend()
        plt.grid(True, which="both", ls="--", alpha=0.5)
        plt.show()

def format_dataframe(df: pd.DataFrame, colnames: list[str], del_rows: list[int]) -> pd.DataFrame:
    if len(del_rows) > 0:
        df = df.drop(labels=del_rows, axis=0)
        df = df.reset_index(drop=True)
    if len(colnames) > 0:
        if len(colnames) != df.shape[1]:
            raise ValueError(f"Dataframe has {df.shape[1]} columns but colnames list has {len(colnames)} entries.")
        df.columns = colnames
    return df


def main() -> None:
    
    parser = argparse.ArgumentParser(
        description="Convert a space-separated text file into comma-separated values."
    )
    parser.add_argument(
        "input_file", 
        help="Path to the input file with space-separated values.", 
        default=DEFAULT_INPUT_FILE,
        nargs="?"
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        help="Optional output file path. Defaults to input file name with .csv extension.",
    )
    args = parser.parse_args()

    input_path = pathlib.Path(args.input_file).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    converter = TableConverter()
    df = converter.read_file(input_path)

    # S_Mean is the mean value submitted by the student
    # S_Blanked is the blanked value submitted by the student
    colnames = ["ID","Conc","Abs1", "Abs2", "S_Mean", "S_Blanked"]
    df.columns = colnames

    # Process the data using StandardCurveAnalyser
    # First column has an index of 0

    analyser = StandardCurveAnalyser(df, 1,2,3)
    df = analyser.calculate_std_curve()
    reg = analyser.linear_regression(1,7)
    r_squared = analyser.r_squared_forced_through_origin(1,7)
    print(df)
    print(f"Slope: {reg[0]:.4f}, Intercept: {reg[1]:.4f}")
    print(f"R-squared: {r_squared:.4f}")

    # Write to Excel
    writer = ExcelWriter()
    excel_output_path = DEFAULT_EXCEL_FILE
    raw_data = df.iloc[:, [2,3]]
    writer.write_dataframe_to_excel(raw_data, pathlib.Path(excel_output_path), "Table 3", 3, 6)
    print(f"Data written to Excel file: {excel_output_path}")


if __name__ == "__main__":
    main()
