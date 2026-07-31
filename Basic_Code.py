# Week 1 – Core Data Analytics Foundation
import io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def main():
    """Create a sample sales dataset, clean it, analyze it, and visualize results."""
    try:
        # Create a dummy CSV dataset in memory using io.StringIO
        csv_data = """Date,Category,Quantity,Revenue
2024-01-01,Electronics,2,1200
2024-01-02,Apparel,3,450
2024-01-03,Electronics,1,600
2024-01-04,Home,4,800
2024-01-05,Apparel,2,300
2024-01-06,Home,3,900
2024-01-07,Electronics,5,3000
2024-01-08,Home,,700
2024-01-09,Apparel,2,not_a_number
"""

        # Load data into a Pandas DataFrame
        df = pd.read_csv(io.StringIO(csv_data))

        # Clean the dataset
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
        df['Revenue'] = pd.to_numeric(df['Revenue'], errors='coerce')

        # Drop rows with missing values after cleaning
        df = df.dropna().reset_index(drop=True)

        # Basic validation: confirm the DataFrame is not empty
        if df.empty:
            print("No valid data available after cleaning.")
            return

        # KPI calculations using NumPy
        total_revenue = np.sum(df['Revenue'])
        total_orders = len(df)
        aov = total_revenue / total_orders if total_orders else 0
        top_selling_category = df.groupby('Category')['Quantity'].sum().idxmax()

        # Print KPI results to the console
        print("Sales Data Analysis")
        print("-" * 30)
        print(f"Total Revenue: ${total_revenue:,.2f}")
        print(f"Total number of orders: {total_orders}")
        print(f"Average Order Value (AOV): ${aov:,.2f}")
        print(f"Top-Selling Category: {top_selling_category}")

        # Prepare data for visualization
        revenue_by_category = df.groupby('Category')['Revenue'].sum().sort_values(ascending=False)
        daily_units_sold = df.groupby('Date')['Quantity'].sum().sort_index()

        # Create a single figure with 1 row and 2 columns
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        # Bar chart: Total Revenue by Category
        axes[0].bar(revenue_by_category.index, revenue_by_category.values, color='steelblue')
        axes[0].set_title('Total Revenue by Category')
        axes[0].set_xlabel('Category')
        axes[0].set_ylabel('Revenue')
        axes[0].tick_params(axis='x', rotation=45)

        # Line chart: Daily Units Sold over time
        axes[1].plot(daily_units_sold.index, daily_units_sold.values, marker='o', color='tomato')
        axes[1].set_title('Daily Units Sold')
        axes[1].set_xlabel('Date')
        axes[1].set_ylabel('Units Sold')
        axes[1].tick_params(axis='x', rotation=45)

        fig.tight_layout()
        plt.show()

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
