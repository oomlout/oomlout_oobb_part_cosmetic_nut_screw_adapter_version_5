$fn = 100;

difference() {
    cylinder(h=4.2, d=12);
    translate([0, 0, 0])
        cylinder(h=4.2, r1=2.375, r2=4.5);
    translate([0, 0, -1])
        cylinder(h=6.2, r=2.375);
}
