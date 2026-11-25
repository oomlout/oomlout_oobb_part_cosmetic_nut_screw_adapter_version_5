$fn = 100;

translate([0, 0, 4.2]) rotate([180, 0, 0])
difference() {
    union() {
        cylinder(h=4.2, d=12);
        translate([0, 0, -3]) cylinder(h=3, d=5.75);
    }
    translate([0, 0, 0]) cylinder(h=4.2, r1=2.375, r2=4.5);
    translate([0, 0, -4]) cylinder(h=9.2, r=2.375);
}
