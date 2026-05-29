import plotly.express as px
from .base import IVisualizationDriver, MatplotlibVisualizationResult, PlotlyVisualizationResult

class StatusDistributionDriver(IVisualizationDriver):
    def visualize(self):
        if len(self.df) == 0:
            return MatplotlibVisualizationResult(
                "List Status Breakdown", self.get_not_enough_data_image()
            )

        status_counts = self.df["my_status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]

        if self.opts.interactive_charts:
            fig = px.pie(
                status_counts, 
                values="Count", 
                names="Status", 
                hole=0.4, 
                title="List Status Breakdown",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            return PlotlyVisualizationResult("List Status Breakdown", fig)

        # Matplotlib fallback
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.pie(status_counts["Count"], labels=status_counts["Status"], autopct='%1.1f%%', startangle=140, wedgeprops=dict(width=0.4))
        ax.set_title("List Status Breakdown")
        return MatplotlibVisualizationResult("List Status Breakdown", self.b64_image_from_plt_fig(fig))
