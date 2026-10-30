// MediCare Pro - Point of Sale (POS) Billing Engine
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('posSearchInput');
  const searchResults = document.getElementById('posSearchResults');
  const cartBody = document.getElementById('posCartBody');
  const emptyCartRow = document.getElementById('emptyCartRow');
  
  const subtotalEl = document.getElementById('summarySubtotal');
  const discountEl = document.getElementById('summaryDiscount');
  const taxEl = document.getElementById('summaryTax');
  const grandTotalEl = document.getElementById('summaryGrandTotal');
  const amountPaidInput = document.getElementById('amountPaidInput');
  const changeDueEl = document.getElementById('summaryChangeDue');
  const hiddenCartData = document.getElementById('hiddenCartData');
  const checkoutBtn = document.getElementById('checkoutBtn');
  const posForm = document.getElementById('posForm');
  
  const customerPhoneInput = document.getElementById('customerPhoneInput');
  const customerNameInput = document.getElementById('customerNameInput');
  const customerIdInput = document.getElementById('customerIdInput');

  let cart = [];
  let debounceTimeout = null;

  // Search Medicines with debounce
  if (searchInput) {
    searchInput.focus();

    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimeout);
      const query = searchInput.value.trim();

      if (query.length < 1) {
        searchResults.style.display = 'none';
        searchResults.innerHTML = '';
        return;
      }

      debounceTimeout = setTimeout(() => {
        fetch(`/api/medicines/search?q=${encodeURIComponent(query)}&include_expired=0`)
          .then(res => res.json())
          .then(data => renderSearchResults(data))
          .catch(err => console.error("Search error:", err));
      }, 250);
    });

    // Close search results when clicking outside
    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.style.display = 'none';
      }
    });

    // Keyboard shortcut '/' to focus search
    document.addEventListener('keydown', (e) => {
      if (e.key === '/' && document.activeElement !== searchInput && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
    });
  }

  function renderSearchResults(medicines) {
    if (!medicines || medicines.length === 0) {
      searchResults.innerHTML = '<div style="padding: 0.85rem; color: #64748b; font-size: 0.85rem;">No active medicines with available stock found.</div>';
      searchResults.style.display = 'block';
      return;
    }

    let html = '<div class="search-results-list" style="max-height: 280px; overflow-y: auto;">';
    medicines.forEach(med => {
      if (med.batches && med.batches.length > 0) {
        med.batches.forEach(batch => {
          html += `
            <div class="search-result-item" 
                 data-med-id="${med.id}"
                 data-med-name="${escapeHtml(med.name)}"
                 data-med-code="${escapeHtml(med.code)}"
                 data-batch-id="${batch.id}"
                 data-batch-num="${escapeHtml(batch.batch_number)}"
                 data-exp-date="${batch.expiry_date}"
                 data-price="${batch.selling_price}"
                 data-stock="${batch.quantity}"
                 style="padding: 0.65rem 0.85rem; border-bottom: 1px solid #e2e8f0; cursor: pointer; display: flex; align-items: center; justify-content: space-between; transition: background 0.15s ease;">
              <div>
                <div style="font-weight: 600; color: #0f172a; font-size: 0.875rem;">
                  ${escapeHtml(med.name)} <span style="font-size: 0.75rem; color: #64748b; font-weight: 500;">(${escapeHtml(med.code)})</span>
                </div>
                <div style="font-size: 0.75rem; color: #64748b; display: flex; gap: 0.75rem; margin-top: 0.15rem;">
                  <span>Batch: <strong style="color: #0f172a;">${escapeHtml(batch.batch_number)}</strong></span>
                  <span>Exp: ${batch.expiry_date}</span>
                  <span>Rack: ${escapeHtml(med.rack_location || 'N/A')}</span>
                </div>
              </div>
              <div style="text-align: right;">
                <div style="font-weight: 700; color: #0284c7; font-size: 0.95rem;">₹${Number(batch.selling_price).toFixed(2)}</div>
                <div style="font-size: 0.75rem; color: ${batch.quantity <= 10 ? '#d97706' : '#059669'}; font-weight: 600;">
                  ${batch.quantity} units left
                </div>
              </div>
            </div>
          `;
        });
      } else {
        html += `
          <div style="padding: 0.65rem 0.85rem; border-bottom: 1px solid #e2e8f0; opacity: 0.6; display: flex; justify-content: space-between;">
            <div>
              <div style="font-weight: 600; font-size: 0.875rem;">${escapeHtml(med.name)}</div>
              <div style="font-size: 0.75rem; color: #e11d48;">Out of stock or expired</div>
            </div>
          </div>
        `;
      }
    });
    html += '</div>';

    searchResults.innerHTML = html;
    searchResults.style.display = 'block';

    // Click handler for items
    searchResults.querySelectorAll('.search-result-item').forEach(el => {
      el.addEventListener('click', () => {
        addItemToCart({
          medicine_id: parseInt(el.getAttribute('data-med-id')),
          medicine_name: el.getAttribute('data-med-name'),
          medicine_code: el.getAttribute('data-med-code'),
          batch_id: parseInt(el.getAttribute('data-batch-id')),
          batch_number: el.getAttribute('data-batch-num'),
          expiry_date: el.getAttribute('data-exp-date'),
          unit_price: parseFloat(el.getAttribute('data-price')),
          stock: parseInt(el.getAttribute('data-stock')),
          quantity: 1,
          discount: 0.0,
          tax_percent: 12.0 // Standard GST 12%
        });

        searchInput.value = '';
        searchResults.style.display = 'none';
        searchInput.focus();
      });

      el.addEventListener('mouseenter', () => el.style.backgroundColor = '#f1f5f9');
      el.addEventListener('mouseleave', () => el.style.backgroundColor = 'transparent');
    });
  }

  function addItemToCart(item) {
    // Check if batch is already in cart
    const existingIndex = cart.findIndex(c => c.batch_id === item.batch_id);

    if (existingIndex > -1) {
      if (cart[existingIndex].quantity + 1 > cart[existingIndex].stock) {
        alert(`Cannot add more. Available stock for batch ${item.batch_number} is only ${item.stock} units.`);
        return;
      }
      cart[existingIndex].quantity += 1;
    } else {
      if (item.stock < 1) {
        alert(`Batch ${item.batch_number} is out of stock.`);
        return;
      }
      cart.push(item);
    }

    renderCart();
  }

  function renderCart() {
    if (cart.length === 0) {
      if (emptyCartRow) emptyCartRow.style.display = 'table-row';
      cartBody.innerHTML = '';
      if (emptyCartRow) cartBody.appendChild(emptyCartRow);
      updateTotals();
      return;
    }

    if (emptyCartRow) emptyCartRow.style.display = 'none';
    cartBody.innerHTML = '';

    cart.forEach((item, index) => {
      const lineTotal = calculateLineTotal(item);
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight: 600;">
          ${escapeHtml(item.medicine_name)}
          <div style="font-size: 0.75rem; color: #64748b;">
            Batch: ${escapeHtml(item.batch_number)} | Exp: ${item.expiry_date}
          </div>
        </td>
        <td style="text-align: center;">
          <input type="number" class="qty-input item-qty" data-index="${index}" min="1" max="${item.stock}" value="${item.quantity}">
          <div style="font-size: 0.7rem; color: #64748b;">Max: ${item.stock}</div>
        </td>
        <td style="text-align: right; font-weight: 500;">
          ₹${item.unit_price.toFixed(2)}
        </td>
        <td style="text-align: center;">
          <input type="number" class="qty-input item-disc" data-index="${index}" min="0" step="1" value="${item.discount || 0}" style="width: 55px;">
        </td>
        <td style="text-align: center;">
          <select class="form-select item-tax" data-index="${index}" style="padding: 0.25rem 0.4rem; font-size: 0.75rem; width: 65px;">
            <option value="0" ${item.tax_percent === 0 ? 'selected' : ''}>0%</option>
            <option value="5" ${item.tax_percent === 5 ? 'selected' : ''}>5%</option>
            <option value="12" ${item.tax_percent === 12 ? 'selected' : ''}>12%</option>
            <option value="18" ${item.tax_percent === 18 ? 'selected' : ''}>18%</option>
          </select>
        </td>
        <td style="text-align: right; font-weight: 700; color: #0284c7;">
          ₹${lineTotal.toFixed(2)}
        </td>
        <td style="text-align: center;">
          <button type="button" class="btn btn-sm btn-danger remove-item-btn" data-index="${index}" style="padding: 0.25rem 0.5rem;" title="Remove">
            ✕
          </button>
        </td>
      `;
      cartBody.appendChild(tr);
    });

    // Attach row events
    cartBody.querySelectorAll('.item-qty').forEach(input => {
      input.addEventListener('change', (e) => {
        const idx = parseInt(e.target.getAttribute('data-index'));
        let val = parseInt(e.target.value);
        if (isNaN(val) || val < 1) val = 1;
        if (val > cart[idx].stock) {
          alert(`Quantity cannot exceed available batch stock (${cart[idx].stock} units).`);
          val = cart[idx].stock;
        }
        cart[idx].quantity = val;
        renderCart();
      });
    });

    cartBody.querySelectorAll('.item-disc').forEach(input => {
      input.addEventListener('change', (e) => {
        const idx = parseInt(e.target.getAttribute('data-index'));
        let val = parseFloat(e.target.value);
        if (isNaN(val) || val < 0) val = 0.0;
        cart[idx].discount = val;
        renderCart();
      });
    });

    cartBody.querySelectorAll('.item-tax').forEach(select => {
      select.addEventListener('change', (e) => {
        const idx = parseInt(e.target.getAttribute('data-index'));
        cart[idx].tax_percent = parseFloat(e.target.value);
        renderCart();
      });
    });

    cartBody.querySelectorAll('.remove-item-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(btn.getAttribute('data-index'));
        cart.splice(idx, 1);
        renderCart();
      });
    });

    updateTotals();
  }

  function calculateLineTotal(item) {
    const gross = item.quantity * item.unit_price;
    const taxable = Math.max(0, gross - (item.discount || 0));
    const tax = taxable * ((item.tax_percent || 0) / 100);
    return taxable + tax;
  }

  function updateTotals() {
    let subtotal = 0.0;
    let totalDiscount = 0.0;
    let totalTax = 0.0;
    let grandTotal = 0.0;

    cart.forEach(item => {
      const gross = item.quantity * item.unit_price;
      const disc = item.discount || 0.0;
      const taxable = Math.max(0, gross - disc);
      const tax = taxable * ((item.tax_percent || 0) / 100);

      subtotal += gross;
      totalDiscount += disc;
      totalTax += tax;
      grandTotal += (taxable + tax);
    });

    if (subtotalEl) subtotalEl.textContent = `₹${subtotal.toFixed(2)}`;
    if (discountEl) discountEl.textContent = `-₹${totalDiscount.toFixed(2)}`;
    if (taxEl) taxEl.textContent = `₹${totalTax.toFixed(2)}`;
    if (grandTotalEl) grandTotalEl.textContent = `₹${grandTotal.toFixed(2)}`;

    // Sync hidden input for form post
    if (hiddenCartData) {
      hiddenCartData.value = JSON.stringify(cart);
    }

    calculateChange(grandTotal);
  }

  function calculateChange(grandTotal) {
    if (!amountPaidInput || !changeDueEl) return;
    const paid = parseFloat(amountPaidInput.value) || 0.0;
    const change = Math.max(0.0, paid - grandTotal);
    changeDueEl.textContent = `₹${change.toFixed(2)}`;
  }

  if (amountPaidInput) {
    amountPaidInput.addEventListener('input', () => {
      const gTotalStr = grandTotalEl ? grandTotalEl.textContent.replace('₹', '') : '0';
      calculateChange(parseFloat(gTotalStr) || 0.0);
    });
  }

  // Tender Buttons
  document.querySelectorAll('.tender-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const val = btn.getAttribute('data-val');
      const gTotalStr = grandTotalEl ? grandTotalEl.textContent.replace('₹', '') : '0';
      const grandTotal = parseFloat(gTotalStr) || 0.0;

      if (val === 'exact') {
        amountPaidInput.value = grandTotal.toFixed(2);
      } else {
        amountPaidInput.value = parseFloat(val).toFixed(2);
      }
      calculateChange(grandTotal);
    });
  });

  // Customer phone lookup
  if (customerPhoneInput) {
    customerPhoneInput.addEventListener('input', () => {
      const phone = customerPhoneInput.value.trim();
      if (phone.length >= 10) {
        fetch(`/api/customers/lookup?phone=${encodeURIComponent(phone)}`)
          .then(res => res.json())
          .then(data => {
            if (data && customerNameInput) {
              customerNameInput.value = data.name;
              if (customerIdInput) customerIdInput.value = data.id;
            }
          })
          .catch(err => console.error("Customer lookup error:", err));
      }
    });
  }

  // Form Submission
  if (posForm) {
    posForm.addEventListener('submit', (e) => {
      if (cart.length === 0) {
        e.preventDefault();
        alert("Your billing cart is empty! Please search and select at least one medicine.");
        return;
      }

      if (checkoutBtn) {
        checkoutBtn.disabled = true;
        checkoutBtn.innerHTML = 'Processing Sale...';
      }
    });
  }

  function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;')
               .replace(/"/g, '&quot;')
               .replace(/'/g, '&#039;');
  }
});
