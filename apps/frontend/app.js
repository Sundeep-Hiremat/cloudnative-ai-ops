const API_BASE = ""; // Relative path to backend APIs

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  fetchOrders();

  document.getElementById("create-order-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    await createOrder();
  });
});

async function checkHealth() {
  const healthEl = document.getElementById("health-status");
  const readyEl = document.getElementById("ready-status");

  try {
    const hRes = await fetch(`${API_BASE}/health`);
    if (hRes.ok) {
      healthEl.innerHTML = '<span class="dot green"></span> Health: OK';
    } else {
      healthEl.innerHTML = '<span class="dot red"></span> Health: FAIL';
    }
  } catch (err) {
    healthEl.innerHTML = '<span class="dot red"></span> Health: DOWN';
  }

  try {
    const rRes = await fetch(`${API_BASE}/ready`);
    if (rRes.ok) {
      readyEl.innerHTML = '<span class="dot green"></span> DB: Connected';
    } else {
      readyEl.innerHTML = '<span class="dot red"></span> DB: Error';
    }
  } catch (err) {
    readyEl.innerHTML = '<span class="dot red"></span> DB: Unreachable';
  }
}

async function fetchOrders() {
  const tbody = document.getElementById("orders-tbody");
  tbody.innerHTML = '<tr><td colspan="8" class="text-center">Loading orders...</td></tr>';

  try {
    const res = await fetch(`${API_BASE}/api/orders`);
    if (!res.ok) throw new Error("Failed to fetch orders");
    const orders = await res.json();

    if (orders.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center">No orders created yet. Use the form to add one!</td></tr>';
      return;
    }

    tbody.innerHTML = orders.map(order => {
      const createdDate = new Date(order.created_at).toLocaleString();
      let statusClass = "badge-pending";
      if (order.status === "COMPLETED") statusClass = "badge-completed";
      if (order.status === "CANCELLED") statusClass = "badge-cancelled";

      return `
        <tr>
          <td>#${order.id}</td>
          <td><strong>${escapeHtml(order.customer_name)}</strong></td>
          <td>${escapeHtml(order.item_name)}</td>
          <td>${order.quantity}</td>
          <td>$${order.total_price.toFixed(2)}</td>
          <td><span class="badge ${statusClass}">${order.status}</span></td>
          <td style="font-size: 12px; color: var(--text-muted);">${createdDate}</td>
          <td>
            ${order.status === "PENDING" ? `
              <button class="btn btn-secondary btn-sm" onclick="updateStatus(${order.id}, 'COMPLETED')">Complete</button>
            ` : ''}
            <button class="btn btn-danger btn-sm" onclick="deleteOrder(${order.id})">Delete</button>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center" style="color: var(--danger);">Error loading orders: ${err.message}</td></tr>`;
  }
}

async function createOrder() {
  const payload = {
    customer_name: document.getElementById("customer_name").value,
    item_name: document.getElementById("item_name").value,
    quantity: parseInt(document.getElementById("quantity").value),
    total_price: parseFloat(document.getElementById("total_price").value)
  };

  try {
    const res = await fetch(`${API_BASE}/api/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      document.getElementById("create-order-form").reset();
      await fetchOrders();
    } else {
      alert("Error creating order");
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

async function updateStatus(id, newStatus) {
  try {
    const res = await fetch(`${API_BASE}/api/orders/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });

    if (res.ok) {
      await fetchOrders();
    }
  } catch (err) {
    alert(`Error updating order: ${err.message}`);
  }
}

async function deleteOrder(id) {
  if (!confirm(`Are you sure you want to delete order #${id}?`)) return;

  try {
    const res = await fetch(`${API_BASE}/api/orders/${id}`, {
      method: "DELETE"
    });

    if (res.status === 204) {
      await fetchOrders();
    }
  } catch (err) {
    alert(`Error deleting order: ${err.message}`);
  }
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
