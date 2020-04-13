function renderGlobalPlot() {
    d3.json("/global_data").then((global_data) => {
        let frames = []
        let slider_steps =[]
        let n = 11
        let num = "2020-01-22"
        
        for (var i=0; i<=n; i++) {
            let z = global_data.Confirmed
            let locations = global_data.Country
            frames[i] = {data: [{z: z, locations, locations, text: locations}],name: num}
            slider_steps.push({
                label: num.toString(),
                method: "animate",
                args: [[num], {
                    mode: "immediate",
                    transistion: {duration:300},
                    frame: {duration: 300}
                }]
            })
            num = num +5
        }
        let data = [{
            type: "choropleth",
            locationmode: "countries",
            locations: frames[0].data[0].locations,
            z: frames[0].data.z,
            text: frames[0].data[0].locations,
            zauto: false,
            zmin:30,
            zmax: 90
        }]
        let layout = {
            title: "Corona Virus Spread",
            geo: {
                scope: "world",
                countrycolor: 'rgb(255, 255, 255)',
                showland: true,
                landcolor: 'rgb(217, 217, 217)',
                showlakes: true,
                lakecolor: 'rgb(255, 255, 255)',
                subunitcolor: 'rgb(255, 255, 255)',
                lonaxis: {},
                lataxis: {}
            },
            updatemenus: [{
                x: 0.1,
                y: 0,
                yanchor: "top",
                xanchor: "right",
                showactive: false,
                direction: "left",
                type: "buttons",
                pad: {"t": 87, "r": 10},
                buttons: [{
                  method: "animate",
                  args: [null, {
                    fromcurrent: true,
                    transition: {
                      duration: 200,
                    },
                    frame: {
                      duration: 500
                    }
                  }],
                  label: "Play"
                }, {
                  method: "animate",
                  args: [
                    [null],
                    {
                      mode: "immediate",
                      transition: {
                        duration: 0
                      },
                      frame: {
                        duration: 0
                      }
                    }
                  ],
                  label: "Pause"
                }]
            }],
            sliders: [{
                active: 0,
                steps: slider_steps,
                x: 0.1,
                len: 0.9,
                xanchor: "left",
                y: 0,
                yanchor: "top",
                pad: {t: 50, b: 10},
                currentvalue: {
                  visible: true,
                  prefix: "Year:",
                  xanchor: "right",
                  font: {
                    size: 20,
                    color: "#666"
                  }
                },
                transition: {
                  duration: 300,
                  easing: "cubic-in-out"
                }
              }]
        }
        Plotly.newPlot('global-cases', data, layout).then(function() {
            Plotly.addFrames('global-cases', frames);
          })
    })
}


renderGlobalPlot()