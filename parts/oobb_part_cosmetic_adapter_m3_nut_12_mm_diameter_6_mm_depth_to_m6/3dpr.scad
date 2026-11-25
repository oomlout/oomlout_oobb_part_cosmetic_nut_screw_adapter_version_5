$fn = 100;

translate([0, 0, 4.5]) rotate([180, 0, 0])
difference() {
    union() {
        cylinder(h=4.5, d=12);
        translate([0, 0, -1.5]) cylinder(h=1.5, d=5.75);
    }
    translate([0, 0, 2]) cylinder(h=2.5, r=3.462, $fn=6);
    translate([0, 0, -2.5]) cylinder(h=8, r=1.8);
}
