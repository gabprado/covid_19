function buildCountrySnapshot(country, dataPoint) {
    d3.json(`/global_data/${country}/${dataPoint}`).then((country_data) => {
        let trace1 = {
            x: country_data.Date,
            y: country_data.Confirmed_Cases,
            type: "bar"  
        }
        let data = [trace1]
        Plotly.newPlot("country_snapshot", data)
        console.log(country_data)
     console.log(country_data.Date)
    console.log(country_data.Confirmed_Cases)
    })
    
};
buildCountrySnapshot("US","Confirmed_Cases")