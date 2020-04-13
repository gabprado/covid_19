const countrySelect = d3.select("#country")

function get_country_options() {
    d3.json("country_list").then((data) => {
        let countries = data.Country.filter(function(value, index, self) {
            return index == self.indexOf(value)
        })
        countries.forEach(sv => {
            if (sv != "US") {
                const selectOption = countrySelect.append("option")
                selectOption.text(sv)
                selectOption.property("value", sv)
            }
        })
    })    
}

function updateFilters() {
    const changedElement = d3.select(this).select("select");
    const elementValue = changedElement.property("value");
    buildCountrySnapshot(elementValue,"confirmed")
    buildCountrySnapshot(elementValue,"deaths")
    buildCountrySnapshot(elementValue,"recovered")
    renderAnalysis(elementValue) 
}

function renderAnalysis(country) {
    d3.json(`/global_data/${country}`).then((analysisData) => {
        d3.select("#country-label").html(country)
        d3.select("#summary-text").html(analysisData.Analysis_Summary)
        // let data = [{
        //     type: "indicatior",
        //     mode: "number+delta",
        //     number: {
        //         prefix: "$"
        //     },
        //     value: 400,
        //     delta:{
        //         position: "top",
        //         reference: 320
        //     },
        //     domain: {
        //         x: [0,1],
        //         y: [0,1]
        //     }
        // }]
        // let layout = {
        //     paper_bgcolor: "lightgray",
        //     width: 600,
        //     height:200,
        //     margin: {
        //         t: 0,
        //         b: 0,
        //         l: 0,
        //         r: 0
        //     }
        // }
        // Plotly.newPlot("current-case-avg",data, layout)
        let data = [
            {
              type: "indicator",
              mode: "delta",
              value: analysisData.Analysis_Confirmed_Status,
              delta: { position: "top", reference: 0 },
              domain: { x: [0, 1], y: [0, 1] }
            }
          ];
          let layout = {
            paper_bgcolor: "white",
            // width: 200,
             height: 50,
            margin: { t: 0, b: 0, l: 0, r: 0 }
          };
          
          Plotly.newPlot('current-case-avg', data, layout);
    })

}

function buildCountrySnapshot(country, metric) {
    d3.json(`/global_data/${country}`).then((country_data) => {
        if (metric === "deaths") {
            avgDataPoint = country_data.Five_Day_Avg_Deaths
            actualDataPoint = country_data.Deltas_Deaths
            plotTag = "snapshot_deaths"
            yAxisLabel = "New Deaths"
        } else if (metric === "recovered") {
            avgDataPoint = country_data.Five_Day_Avg_Recovered
            actualDataPoint = country_data.Deltas_Recovered
            plotTag = "snapshot_recovered"
            yAxisLabel = "New Recovered"
        } else {
            avgDataPoint = country_data.Five_Day_Avg_Confirmed
            actualDataPoint = country_data.Deltas_Confirmed
            plotTag = "snapshot_confirmed"
            yAxisLabel = "Confirmed New Cases"
        }
        let trace1 = {
            x: country_data.Date,
            y: avgDataPoint,
            marker: {
                color: "#024F0C"
            },
            name: "Five Day Moving Average",
            type: "scatter"
        };
        let trace2 = {
            x: country_data.Date,
            y: actualDataPoint,
            marker: {
                color: "#A0BDA4"
            },
            name: "Actual Data",
            type: "bar"
        };
        let layout = {
            yaxis: {
                title: yAxisLabel
            },
            legend: {
                x: 0,
                y: -.15,
                orientation: "h"
            } 
        }

        let data = [trace1, trace2]
        Plotly.newPlot(plotTag, data, layout)
    
    })
    
};
d3.selectAll(".filter").on("change", updateFilters)
renderAnalysis("US") 
buildCountrySnapshot("US", "confirmed")
buildCountrySnapshot("US", "deaths")
buildCountrySnapshot("US", "recovered")
get_country_options()



