import React from 'react';

function OrderItem({ order }) {
  return (
    <div>
      <h3>Order ID: {order.id}</h3>
      <p>Product: {order.product}</p>
      <p>Quantity: {order.quantity}</p>
      <p>Status: {order.status}</p>
    </div>
  );
}

export default OrderItem;