$(function() {
    var user = $('.dropdown button').html().split(", ")[1];
    $("#inp-date").on("change",function(){
        var selected = $(this).val();
        var path = window.location.pathname
        const splitArr = path.split("/");
        var sport = "badminton";
        if (splitArr.at(-1) !== "booking-front"){
            sport = splitArr.at(-3);
        };
        window.location.pathname = user + '/booking/'+ sport + '/_/' + selected;
    });

    $('.tab-sport-item a').on('click', function() {
        var sport = $(this).text().toLowerCase();;
        var currDate = $("#inp-date").val();
        window.location.pathname = user + '/booking/'+ sport + '/_/' + currDate;
    });

});