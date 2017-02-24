$(document).ready(function(){

    var setOrgCountNumberInPage = function(count) {
        var count_text = $('.number-of-results').text();
        var count_str = count.toString();
        if(count >= 1000) {
            count_str = count_str.slice(0, 1) + " " + count_str.slice(1);
        }
        var replaced = count_text.replace(/\d[\s,]?\d+|\d/g, count_str);
        $('.number-of-results').text(replaced);
        if($('.number-of-results').css('visibility') == 'hidden') {
            $('.number-of-results').css('display', 'none');
            $('.number-of-results').css('visibility', 'visible');
            $('.number-of-results').fadeIn();
        }
    }

    $('[data-organization-tree] .js-expand').bind('click', function(){
        $(this).siblings('.js-collapse, .js-collapsed').show();
        $(this).hide();
    });

    $('[data-organization-tree] .js-collapse').bind('click', function(){
        $(this).hide().siblings('.js-collapsed').hide();
        $(this).siblings('.js-expand').show();
    });

    $('[data-organization-filter]').bind('keyup cut paste', function(){
        var search_str = $(this).val().toLowerCase();

        if (search_str.length != 0){
            $('.js-collapse, .js-expand').hide();
            $('.js-collapsed').show();
            $('span.highlight').contents().unwrap();
            var organizations = $('li.organization').filter(function() { return $(this).css('display') != 'none'}).find('.organization-row');
            organizations.hide();
            var count = 0;

            organizations.filter(function(index, element){
                return element.textContent.toLowerCase().indexOf(search_str) >= 0
            }).each(function(index, element){
                var text = $(element).find('a').get(0).textContent;
                var str_index = text.toLowerCase().indexOf(search_str);

                if (str_index >= 0){
                    count++;
                    $(this).find('a').html(text.substr(0, str_index) + '<span class="highlight">' + text.substr(str_index, search_str.length) + '</span>' + text.substr(str_index + search_str.length))[0];
                }

                // show direct parent nodes, too
                $(element).parents('.organization').each(function(index, element) {
                    $(element).show().children().not('.btn-collapse').show();
                });

            }).show();

        }
        else {
            count = $('li.organization').filter(function() { return $(this).css('display') != 'none'}).length;
            $('span.highlight').contents().unwrap()
            $('.organization-row').show();
            $('[data-organization-tree] .js-collapse').trigger('click');
        }
        setOrgCountNumberInPage(count);

    })

    // Default: Hide organizations without datasets
    $('.organization-empty').hide();

    $('#show-empty-organizations').click(function() {
        $('[data-organization-filter]').val('');
        $('[data-organization-filter]').trigger('keyup');
        if ($(this).is(':checked')) {
          $('.organization-empty').show();
        }
        else {
          $('.organization-empty').hide();
        }
        var shown_count = $('li.organization').filter(function() { return $(this).css('display') != 'none'}).length;
        setOrgCountNumberInPage(shown_count);
    });

    var shown_count = $('li.organization').filter(function() { return $(this).css('display') != 'none'}).length;
    setOrgCountNumberInPage(shown_count);
    $('[data-organization-tree] .js-expand').click();
    $('[data-organization-tree] .organization-row a').last().css('text-decoration', 'underline');
});