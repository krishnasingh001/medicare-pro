// MediCare Pro - Chart.js Visualizations
document.addEventListener('DOMContentLoaded', () => {
  const salesCanvas = document.getElementById('salesTrendChart');
  const catCanvas = document.getElementById('categoryDistChart');

  if (!salesCanvas && !catCanvas) return;

  fetch('/api/dashboard/chart_data')
    .then(res => res.json())
    .then(data => {
      // 1. Sales Trend Chart
      if (salesCanvas && data.sales_trend) {
        const ctx = salesCanvas.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(2, 132, 199, 0.28)');
        gradient.addColorStop(1, 'rgba(2, 132, 199, 0.01)');

        new Chart(salesCanvas, {
          type: 'line',
          data: {
            labels: data.sales_trend.labels,
            datasets: [{
              label: 'Daily Sales Revenue (₹)',
              data: data.sales_trend.values,
              borderColor: '#0284c7',
              borderWidth: 2.5,
              backgroundColor: gradient,
              fill: true,
              tension: 0.35,
              pointBackgroundColor: '#0284c7',
              pointBorderColor: '#ffffff',
              pointBorderWidth: 2,
              pointRadius: 4,
              pointHoverRadius: 6
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: '#0f172a',
                padding: 10,
                callbacks: {
                  label: (ctx) => ` Revenue: ₹${ctx.parsed.y.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                }
              }
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { font: { size: 11, family: 'Inter' }, color: '#64748b' }
              },
              y: {
                beginAtZero: true,
                grid: { color: '#f1f5f9' },
                ticks: {
                  font: { size: 11, family: 'Inter' },
                  color: '#64748b',
                  callback: (val) => `₹${val}`
                }
              }
            }
          }
        });
      }

      // 2. Category Distribution Chart
      if (catCanvas && data.category_distribution && data.category_distribution.labels.length > 0) {
        const colors = [
          '#0284c7', // Sky blue
          '#0d9488', // Teal
          '#059669', // Emerald
          '#6366f1', // Indigo
          '#d97706', // Amber
          '#e11d48'  // Rose
        ];

        new Chart(catCanvas, {
          type: 'doughnut',
          data: {
            labels: data.category_distribution.labels,
            datasets: [{
              data: data.category_distribution.values,
              backgroundColor: colors.slice(0, data.category_distribution.labels.length),
              borderWidth: 2,
              borderColor: '#ffffff',
              hoverOffset: 4
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '72%',
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  boxWidth: 12,
                  font: { size: 11, family: 'Inter' },
                  padding: 14,
                  color: '#475569'
                }
              },
              tooltip: {
                backgroundColor: '#0f172a',
                padding: 10,
                callbacks: {
                  label: (ctx) => ` ₹${ctx.parsed.toLocaleString('en-IN', { minimumFractionDigits: 2 })} (${ctx.label})`
                }
              }
            }
          }
        });
      }
    })
    .catch(err => console.error("Error loading chart data:", err));
});
