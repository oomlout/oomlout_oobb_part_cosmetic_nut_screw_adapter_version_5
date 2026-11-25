$fn = 100;

difference() {
    cylinder(h=5.5, d=14);
    translate([0, 0, 1])
        cylinder(h=4.5, r1=5.925, r2=6.075);
}
