document.addEventListener("DOMContentLoaded", function() {
    
    // Select all the cards we want to make 3D
    const cards = document.querySelectorAll('.book-card-hover');

    cards.forEach(card => {
        // When the mouse moves over the card
        card.addEventListener('mousemove', function(e) {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left; // X position within the card
            const y = e.clientY - rect.top;  // Y position within the card
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            // Calculate the rotation angle based on mouse position
            // Max rotation is 15 degrees
            const rotateX = ((y - centerY) / centerY) * -15; 
            const rotateY = ((x - centerX) / centerX) * 15;

            // Apply the 3D CSS transform!
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.05, 1.05, 1.05)`;
            card.style.boxShadow = `${-rotateY}px ${rotateX}px 20px rgba(0,0,0,0.4)`;
        });

        // When the mouse leaves, snap the card smoothly back to flat
        card.addEventListener('mouseleave', function() {
            card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
            card.style.boxShadow = `0 8px 32px 0 rgba(0, 0, 0, 0.3)`;
            // Add a smooth transition specifically for the snap-back
            card.style.transition = `transform 0.5s ease, box-shadow 0.5s ease`;
        });
        
        // Remove the transition when hovering again so it instantly tracks the mouse
        card.addEventListener('mouseenter', function() {
            card.style.transition = `none`;
        });
    });

});